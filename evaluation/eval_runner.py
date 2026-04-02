"""评测运行器：批量运行 agent × benchmark 组合并汇总指标。"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from evaluation.metrics import EvalMetrics, load_and_compute


BASE_DIR = Path(__file__).resolve().parents[1]


def _load_eval_config() -> dict:
    cfg_path = BASE_DIR / "configs" / "eval_config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class RunSpec:
    """单次实验运行规格。"""
    agent: str
    benchmark: str
    scope: str
    extra: dict

    @property
    def run_id(self) -> str:
        return f"{self.agent}/{self.benchmark}/{self.scope}"

    def output_dir(self, base: Path) -> Path:
        return base / self.benchmark / self.agent / self.scope


class EvalRunner:
    """评测运行器。"""

    def __init__(self, config: dict | None = None):
        self._cfg = config or _load_eval_config()
        self._output_cfg = self._cfg.get("output", {})
        self._eval_dir = Path(self._output_cfg.get("eval_dir", "outputs/eval_results"))

    def build_run_specs(
        self,
        agents: list[str] | None = None,
        benchmarks: list[str] | None = None,
    ) -> list[RunSpec]:
        """根据配置构建实验矩阵。"""
        matrix = self._cfg.get("experiment_matrix", {})
        agent_list = agents or matrix.get("agents", ["react"])
        bench_cfg = matrix.get("benchmarks", {})

        specs: list[RunSpec] = []
        for agent in agent_list:
            if benchmarks is None or "agentharm" in benchmarks:
                ah_cfg = bench_cfg.get("agentharm", {})
                for subset in ah_cfg.get("subsets", ["harmful"]):
                    specs.append(RunSpec(agent=agent, benchmark="agentharm", scope=subset, extra={}))

            if benchmarks is None or "asb" in benchmarks:
                asb_cfg = bench_cfg.get("asb", {})
                for at in asb_cfg.get("attack_types", ["OPI"]):
                    specs.append(RunSpec(
                        agent=agent, benchmark="asb", scope=at,
                        extra={"task_nums": asb_cfg.get("task_nums", 1)},
                    ))

            if benchmarks is None or "agentdojo" in benchmarks:
                adj_cfg = bench_cfg.get("agentdojo", {})
                for suite in adj_cfg.get("suites", []):
                    for mode in adj_cfg.get("attack_modes", ["injection"]):
                        specs.append(RunSpec(
                            agent=agent, benchmark="agentdojo", scope=f"{suite}_{mode}",
                            extra={"suite": suite, "attack_mode": mode},
                        ))

        return specs

    def run_single(self, spec: RunSpec) -> EvalMetrics:
        """运行单个实验并返回指标。"""
        from agents import get_agent_builder

        print(f"\n[EVAL] {spec.run_id}")
        builder = get_agent_builder(spec.agent)
        agent = builder()

        output_dir = spec.output_dir(self._eval_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        t0 = time.time()

        if spec.benchmark == "agentharm":
            from processors.agentharm import AgentHarmProcessor
            proc = AgentHarmProcessor(agent=agent, output_save_dir=output_dir, subtask=spec.scope)
            if spec.scope == "attack":
                proc.run_attack()
            else:
                proc.run()

        elif spec.benchmark == "asb":
            from processors.asb import ASBProcessor
            proc = ASBProcessor(agent=agent, output_save_dir=output_dir, attack_type=spec.scope)
            proc.run(task_nums=spec.extra.get("task_nums", 1))

        elif spec.benchmark == "agentdojo":
            from processors.agentdojo import AgentDojoProcessor
            proc = AgentDojoProcessor(
                agent=agent, output_save_dir=output_dir,
                suite=spec.extra.get("suite", "banking"),
                attack_mode=spec.extra.get("attack_mode", "injection"),
            )
            proc.run()

        elapsed = time.time() - t0

        meta_path = output_dir / "meta_data.json"
        metrics = load_and_compute(meta_path, spec.agent, spec.benchmark, spec.scope)
        metrics.total_latency = elapsed
        print(f"  ASR={metrics.asr:.2%}  TCR={metrics.tcr:.2%}  ({elapsed:.1f}s)")
        return metrics

    def run_all(
        self,
        agents: list[str] | None = None,
        benchmarks: list[str] | None = None,
    ) -> list[EvalMetrics]:
        """运行完整实验矩阵。"""
        specs = self.build_run_specs(agents=agents, benchmarks=benchmarks)
        results: list[EvalMetrics] = []

        print(f"[EVAL] Total runs: {len(specs)}")
        for i, spec in enumerate(specs, 1):
            print(f"\n--- Run {i}/{len(specs)} ---")
            try:
                m = self.run_single(spec)
                results.append(m)
            except Exception as e:
                print(f"  FAILED: {e}")
                results.append(EvalMetrics(
                    agent=spec.agent, benchmark=spec.benchmark, scope=spec.scope,
                ))

        # 保存汇总
        self._save_summary(results)
        return results

    def _save_summary(self, results: list[EvalMetrics]) -> Path:
        """保存指标汇总到 JSON。"""
        self._eval_dir.mkdir(parents=True, exist_ok=True)
        summary_path = self._eval_dir / "eval_summary.json"
        payload = [m.to_dict() for m in results]
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n[EVAL] Summary saved to {summary_path}")
        return summary_path
