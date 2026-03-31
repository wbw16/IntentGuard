"""训练入口：用构造的数据微调护卫模型。

支持 LoRA / full fine-tune 两种模式。
训练后保存模型到 outputs/guard_models/。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from training.label_schema import (
    TrainingSample,
    _load_training_config,
    compute_distribution,
    validate_sample,
)


class GuardTrainer:
    """护卫模型微调训练器。"""

    def __init__(self) -> None:
        cfg = _load_training_config()
        self._ft_cfg = cfg.get("fine_tuning", {})
        self._sample_cfg = cfg.get("sample_construction", {})
        self._output_dir = Path(self._ft_cfg.get("output_dir", "outputs/guard_models"))
        self._data_dir = Path(self._sample_cfg.get("output_dir", "data/guard_training"))

    def load_samples(self, path: str | Path | None = None) -> list[TrainingSample]:
        """从 JSONL 文件加载训练样本。"""
        data_path = Path(path) if path else self._data_dir / "samples.jsonl"
        if not data_path.exists():
            return []
        samples: list[TrainingSample] = []
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    samples.append(TrainingSample.from_dict(json.loads(line)))
        return samples

    def save_samples(
        self, samples: list[TrainingSample], path: str | Path | None = None,
    ) -> Path:
        """将训练样本保存为 JSONL。"""
        out_path = Path(path) if path else self._data_dir / "samples.jsonl"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for s in samples:
                f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")
        return out_path

    def validate_dataset(self, samples: list[TrainingSample]) -> dict[str, Any]:
        """验证数据集质量并返回统计信息。"""
        errors_by_sample: dict[str, list[str]] = {}
        for s in samples:
            errs = validate_sample(s)
            if errs:
                errors_by_sample[s.sample_id] = errs

        dist = compute_distribution(samples)
        return {
            "distribution": dist,
            "invalid_samples": len(errors_by_sample),
            "total_errors": sum(len(e) for e in errors_by_sample.values()),
            "error_details": errors_by_sample,
        }

    def prepare_sft_data(
        self, samples: list[TrainingSample], output_path: str | Path | None = None,
    ) -> Path:
        """将样本转换为 SFT 格式（messages 格式）。"""
        from guardrail.guard_model_adapter import (
            _CROSS_VALIDATION_SYSTEM,
        )

        out = Path(output_path) if output_path else self._data_dir / "sft_data.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)

        with open(out, "w", encoding="utf-8") as f:
            for s in samples:
                # 构造 SFT 样本：system + user (context) + assistant (label)
                user_content = (
                    f"## User Original Request\n{s.user_query}\n\n"
                    f"## Declared Intent\n{json.dumps(s.intent_declaration, ensure_ascii=False, indent=2)}\n\n"
                    f"## Current Tool Call\nTool: {s.tool_name}\n"
                    f"Parameters: {json.dumps(s.tool_params, ensure_ascii=False, indent=2)}\n\n"
                    f"## Available Tools\n{s.tool_descriptions}\n\n"
                    f"## Action History\n{json.dumps(s.call_history[-5:], ensure_ascii=False)}\n\n"
                    "Evaluate the four cross-validation dimensions and return JSON."
                )

                # 构造期望的 assistant 输出
                assistant_content = json.dumps({
                    "intent_vs_params": {
                        "score": 1.0 - s.risk_level,
                        "contradictions": [s.reason] if s.risk_level > 0.5 else [],
                        "evidence": s.reason,
                    },
                    "intent_vs_user_query": {
                        "score": 1.0 - s.risk_level,
                        "contradictions": [],
                        "evidence": "",
                    },
                    "intent_vs_history": {
                        "score": 1.0 - s.risk_level * 0.5,
                        "contradictions": [],
                        "evidence": "",
                    },
                    "holistic": {
                        "score": 1.0 - s.risk_level,
                        "contradictions": [s.reason] if s.risk_level > 0.5 else [],
                        "evidence": s.reason,
                    },
                    "suggested_modifications": None,
                }, ensure_ascii=False)

                sft_entry = {
                    "messages": [
                        {"role": "system", "content": _CROSS_VALIDATION_SYSTEM},
                        {"role": "user", "content": user_content},
                        {"role": "assistant", "content": assistant_content},
                    ]
                }
                f.write(json.dumps(sft_entry, ensure_ascii=False) + "\n")

        return out

    def train(self, sft_data_path: str | Path | None = None) -> dict[str, Any]:
        """执行微调训练。

        当前为接口定义 + 配置验证。
        实际训练需要 transformers + peft 环境，
        在无 GPU 环境下返回配置摘要。
        """
        data_path = Path(sft_data_path) if sft_data_path else self._data_dir / "sft_data.jsonl"
        if not data_path.exists():
            return {"status": "error", "message": f"SFT data not found: {data_path}"}

        # 统计数据量
        line_count = 0
        with open(data_path, "r") as f:
            for _ in f:
                line_count += 1

        method = self._ft_cfg.get("method", "lora")
        base_model = self._ft_cfg.get("base_model", "Qwen/Qwen2.5-7B-Instruct")
        training_cfg = self._ft_cfg.get("training", {})

        self._output_dir.mkdir(parents=True, exist_ok=True)

        # 检查训练环境
        try:
            import torch
            gpu_available = torch.cuda.is_available()
        except ImportError:
            gpu_available = False

        if not gpu_available:
            return {
                "status": "dry_run",
                "message": "No GPU available. Training config validated.",
                "config": {
                    "base_model": base_model,
                    "method": method,
                    "sft_data": str(data_path),
                    "num_samples": line_count,
                    "epochs": training_cfg.get("epochs", 3),
                    "batch_size": training_cfg.get("batch_size", 4),
                    "learning_rate": training_cfg.get("learning_rate", 2e-5),
                    "output_dir": str(self._output_dir),
                },
            }

        # 实际训练（需要 transformers + peft）
        return self._run_training(base_model, method, data_path, training_cfg)

    def _run_training(
        self,
        base_model: str,
        method: str,
        data_path: Path,
        training_cfg: dict,
    ) -> dict[str, Any]:
        """执行实际训练流程。"""
        try:
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                TrainingArguments,
                Trainer,
            )
            from datasets import load_dataset
        except ImportError:
            return {
                "status": "error",
                "message": "transformers/datasets not installed. "
                           "Run: pip install transformers datasets peft",
            }

        tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(base_model, trust_remote_code=True)

        if method == "lora":
            try:
                from peft import LoraConfig, get_peft_model
                lora_cfg = self._ft_cfg.get("lora", {})
                peft_config = LoraConfig(
                    r=lora_cfg.get("r", 16),
                    lora_alpha=lora_cfg.get("alpha", 32),
                    lora_dropout=lora_cfg.get("dropout", 0.05),
                    target_modules=lora_cfg.get("target_modules", ["q_proj", "v_proj"]),
                    task_type="CAUSAL_LM",
                )
                model = get_peft_model(model, peft_config)
            except ImportError:
                return {"status": "error", "message": "peft not installed. Run: pip install peft"}

        dataset = load_dataset("json", data_files=str(data_path), split="train")
        val_split = self._ft_cfg.get("validation_split", 0.1)
        split = dataset.train_test_split(test_size=val_split)

        args = TrainingArguments(
            output_dir=str(self._output_dir),
            num_train_epochs=training_cfg.get("epochs", 3),
            per_device_train_batch_size=training_cfg.get("batch_size", 4),
            learning_rate=training_cfg.get("learning_rate", 2e-5),
            warmup_ratio=training_cfg.get("warmup_ratio", 0.1),
            weight_decay=training_cfg.get("weight_decay", 0.01),
            gradient_accumulation_steps=training_cfg.get("gradient_accumulation_steps", 4),
            save_strategy="epoch",
            logging_steps=10,
        )

        trainer = Trainer(
            model=model,
            args=args,
            train_dataset=split["train"],
            eval_dataset=split["test"],
            tokenizer=tokenizer,
        )
        trainer.train()
        trainer.save_model(str(self._output_dir / "final"))

        return {
            "status": "completed",
            "output_dir": str(self._output_dir / "final"),
            "train_samples": len(split["train"]),
            "eval_samples": len(split["test"]),
        }
