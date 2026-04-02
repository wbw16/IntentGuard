"""端到端训练数据构造流水线。

用法：
    python -m scripts.run_data_pipeline [--max-scenarios N] [--strategy STRATEGY]

只构造数据集（samples.jsonl + sft_data.jsonl），不执行训练。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

# 确保项目根目录在 sys.path 中
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 加载 .env（不依赖 python-dotenv）
_env_file = ROOT / ".env"
if _env_file.exists():
    import re as _re
    _resolved: dict[str, str] = {}
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _v = _line.split("=", 1)
            # 展开 ${VAR} 引用（先查已解析的，再查 os.environ）
            def _expand(m, _r=_resolved):
                return _r.get(m.group(1)) or os.environ.get(m.group(1), "")
            _v = _re.sub(r"\$\{(\w+)\}", _expand, _v)
            _resolved[_k] = _v
            os.environ.setdefault(_k, _v)  # 不覆盖已有的 shell 变量
    print(f"[INFO] Loaded .env ({len(_resolved)} vars)")

from training.data_collector import DataCollector
from training.trace_generator import TraceGenerator
from training.sample_constructor import SampleConstructor
from training.deception_augmentor import DeceptionAugmentor
from training.train_guard import GuardTrainer
from training.label_schema import compute_distribution


def main():
    parser = argparse.ArgumentParser(description="训练数据构造流水线")
    parser.add_argument("--max-scenarios", type=int, default=3,
                        help="每类数据源最多取几个场景 (default: 3)")
    parser.add_argument("--strategy", default="react",
                        help="agent 策略 (default: react)")
    args = parser.parse_args()
    n = args.max_scenarios

    # ── Step 1: 采集场景 ──────────────────────────────────────────────
    print("=" * 60)
    print("Step 1: 采集攻击/正常场景")
    print("=" * 60)

    collector = DataCollector()

    harmful = collector.collect_agentharm("harmful")[:n]
    print(f"  agentharm/harmful: {len(harmful)} 个场景")

    benign = collector.collect_agentharm("benign")[:max(1, n - 1)]
    print(f"  agentharm/benign:  {len(benign)} 个场景")

    opi = collector.collect_asb("OPI")[:n]
    print(f"  asb/OPI:           {len(opi)} 个场景")

    scenarios = harmful + benign + opi
    print(f"  合计: {len(scenarios)} 个场景")

    if not scenarios:
        print("[ERROR] 没有采集到任何场景，请检查 data/ 目录下的数据文件。")
        sys.exit(1)

    # 构建 scenario_id → scenario 映射
    scenarios_dict = {s.scenario_id: s for s in scenarios}

    # ── Step 2: 生成执行轨迹 ──────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"Step 2: 用 {args.strategy} agent 生成执行轨迹 ({os.environ.get('DEFAULT_MODEL_NAME', 'unknown')})")
    print("=" * 60)

    generator = TraceGenerator()
    traces = []
    for i, scenario in enumerate(scenarios, 1):
        print(f"  [{i}/{len(scenarios)}] {scenario.scenario_id} "
              f"(attack_type={scenario.attack_type.value}) ...", end=" ", flush=True)
        try:
            trace = generator.generate(scenario, args.strategy)
            traces.append(trace)
            step_count = len(trace.steps)
            attacked = "attacked" if trace.was_attacked else "benign"
            succeeded = ", succeeded" if trace.attack_succeeded else ""
            print(f"OK ({step_count} steps, {attacked}{succeeded})")
        except Exception as e:
            print(f"FAILED: {e}")

    print(f"  合计: {len(traces)} 条轨迹")

    if not traces:
        print("[ERROR] 没有生成任何轨迹。")
        sys.exit(1)

    # ── Step 3: 构造训练样本 ──────────────────────────────────────────
    print()
    print("=" * 60)
    print("Step 3: 从轨迹构造训练样本")
    print("=" * 60)

    constructor = SampleConstructor()
    samples = constructor.construct_batch(traces, scenarios_dict)
    print(f"  原始样本数: {len(samples)}")

    # ── Step 4: 欺骗增强 ─────────────────────────────────────────────
    print()
    print("=" * 60)
    print("Step 4: 意图欺骗增强 (规则 fallback)")
    print("=" * 60)

    augmentor = DeceptionAugmentor(llm_client=None)
    samples = augmentor.augment(samples)
    deceptive_count = sum(1 for s in samples if s.is_deceptive_intent)
    print(f"  增强后样本数: {len(samples)} (其中欺骗变体: {deceptive_count})")

    # ── Step 5: 保存 & 生成 SFT 数据 ─────────────────────────────────
    print()
    print("=" * 60)
    print("Step 5: 保存样本 & 生成 SFT 数据")
    print("=" * 60)

    trainer = GuardTrainer()
    model_tag = os.environ.get("DEFAULT_MODEL_NAME", "unknown").replace("/", "_")
    samples_path = trainer.save_samples(samples, model_name=model_tag)
    print(f"  samples → {samples_path}")

    sft_path = trainer.prepare_sft_data(samples, model_name=model_tag)
    print(f"  sft_data → {sft_path}")

    # ── 统计 ──────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("统计摘要")
    print("=" * 60)

    dist = compute_distribution(samples)
    print(f"  总样本数:     {dist['total']}")
    print(f"  标签分布:     {json.dumps(dist['decision_distribution'], indent=None)}")
    print(f"  攻击类型分布: {json.dumps(dist['attack_type_distribution'], indent=None)}")
    print(f"  欺骗样本数:   {dist['deceptive_intent_count']}")

    # 检查 SFT 数据差异化
    with open(sft_path) as f:
        first_line = f.readline().strip()
    if first_line:
        entry = json.loads(first_line)
        assistant_content = json.loads(entry["messages"][2]["content"])
        scores = {
            dim: assistant_content[dim]["score"]
            for dim in ("intent_vs_params", "intent_vs_user_query",
                        "intent_vs_history", "holistic")
        }
        print(f"  SFT 首条四维分数: {scores}")

    print()
    print("Done! 数据集构造完成。")


if __name__ == "__main__":
    main()
