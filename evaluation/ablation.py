"""消融实验模块。

通过环境变量覆盖来禁用 IntentGuard 的各个子模块，
对比完整版与各消融变体的指标差异。
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import yaml

from evaluation.metrics import EvalMetrics, load_and_compute


BASE_DIR = Path(__file__).resolve().parents[1]


def _load_eval_config() -> dict:
    cfg_path = BASE_DIR / "configs" / "eval_config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# 消融变体 → 环境变量覆盖映射
_ABLATION_ENV_OVERRIDES: dict[str, dict[str, str]] = {
    "no_cross_validation": {"INTENTGUARD_DISABLE_CROSS_VALIDATION": "1"},
    "no_intent": {"INTENTGUARD_DISABLE_INTENT": "1"},
    "no_policy": {"INTENTGUARD_DISABLE_POLICY": "1"},
    "no_deception_detection": {"INTENTGUARD_DISABLE_DECEPTION_DETECTION": "1"},
    "binary_only": {"INTENTGUARD_BINARY_DECISIONS": "1"},
}


class AblationRunner:
    """消融实验运行器。"""

    def __init__(self, config: dict | None = None):
        self._cfg = config or _load_eval_config()
        ablation_cfg = self._cfg.get("ablation", {})
        self._variants = ablation_cfg.get("variants", {})
        self._benchmarks = ablation_cfg.get("benchmarks", ["agentharm_harmful", "asb_OPI"])
        output_cfg = self._cfg.get("output", {})
        self._output_dir = Path(output_cfg.get("ablation_dir", "outputs/ablation"))

    def _parse_benchmark(self, bench_str: str) -> tuple[str, str]:
        """解析 'agentharm_harmful' → ('agentharm', 'harmful')。"""
        parts = bench_str.split("_", 1)
        return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], "")

    def run_variant(
        self,
        variant_name: str,
        benchmark: str,
        scope: str,
    ) -> EvalMetrics:
        """运行单个消融变体。"""
        from agents import get_agent_builder

        variant_cfg = self._variants.get(variant_name, {})
        agent_name = variant_cfg.get("agent", "intentguard")

        # 设置环境变量覆盖
        env_overrides = _ABLATION_ENV_OVERRIDES.get(variant_name, {})
        old_env: dict[str, str | None] = {}
        for k, v in env_overrides.items():
            old_env[k] = os.environ.get(k)
            os.environ[k] = v

        try:
            builder = get_agent_builder(agent_name)
            agent = builder()

            output_dir = self._output_dir / variant_name / benchmark / scope
            output_dir.mkdir(parents=True, exist_ok=True)

            t0 = time.time()

            if benchmark == "agentharm":
                from processors.agentharm import AgentHarmProcessor
                proc = AgentHarmProcessor(agent=agent, output_save_dir=output_dir, subtask=scope)
                proc.run()
            elif benchmark == "asb":
                from processors.asb import ASBProcessor
                proc = ASBProcessor(agent=agent, output_save_dir=output_dir, attack_type=scope)
                proc.run(task_nums=1)
            elif benchmark == "agentdojo":
                from processors.agentdojo import AgentDojoProcessor
                proc = AgentDojoProcessor(
                    agent=agent, output_save_dir=output_dir,
                    suite=scope, attack_mode="injection",
                )
                proc.run()

            elapsed = time.time() - t0
            meta_path = output_dir / "meta_data.json"
            metrics = load_and_compute(meta_path, agent_name, benchmark, scope)
            metrics.total_latency = elapsed
            return metrics

        finally:
            # 恢复环境变量
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def run_all(self) -> dict[str, list[EvalMetrics]]:
        """运行所有消融变体 × 所有 benchmark。"""
        results: dict[str, list[EvalMetrics]] = {}

        variant_names = list(self._variants.keys())
        total = len(variant_names) * len(self._benchmarks)
        print(f"[ABLATION] {len(variant_names)} variants × {len(self._benchmarks)} benchmarks = {total} runs")

        idx = 0
        for variant_name in variant_names:
            results[variant_name] = []
            for bench_str in self._benchmarks:
                idx += 1
                benchmark, scope = self._parse_benchmark(bench_str)
                desc = self._variants.get(variant_name, {}).get("description", variant_name)
                print(f"\n--- [{idx}/{total}] {variant_name}: {bench_str} ({desc}) ---")

                try:
                    m = self.run_variant(variant_name, benchmark, scope)
                    results[variant_name].append(m)
                    print(f"  ASR={m.asr:.2%}  TCR={m.tcr:.2%}")
                except Exception as e:
                    print(f"  FAILED: {e}")
                    results[variant_name].append(EvalMetrics(
                        agent="intentguard", benchmark=benchmark, scope=scope,
                    ))

        self._save_summary(results)
        return results

    def _save_summary(self, results: dict[str, list[EvalMetrics]]) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        summary_path = self._output_dir / "ablation_summary.json"
        payload = {
            variant: [m.to_dict() for m in metrics]
            for variant, metrics in results.items()
        }
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n[ABLATION] Summary saved to {summary_path}")
        return summary_path
