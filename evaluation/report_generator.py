"""结果报告生成器：从评测/消融结果生成 Markdown 和 JSON 报告。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.metrics import EvalMetrics


class ReportGenerator:
    """从评测结果生成报告。"""

    def __init__(self, output_dir: str | Path = "outputs/final"):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 主表：agent × benchmark 对比
    # ------------------------------------------------------------------

    def generate_comparison_table(
        self,
        results: list[EvalMetrics],
    ) -> str:
        """生成 agent × benchmark 对比 Markdown 表格。"""
        # 按 (benchmark, scope) 分组列，按 agent 分组行
        benchmarks: list[tuple[str, str]] = []
        seen = set()
        for m in results:
            key = (m.benchmark, m.scope)
            if key not in seen:
                benchmarks.append(key)
                seen.add(key)

        agents = list(dict.fromkeys(m.agent for m in results))

        # 构建查找表
        lookup: dict[tuple[str, str, str], EvalMetrics] = {}
        for m in results:
            lookup[(m.agent, m.benchmark, m.scope)] = m

        # Markdown 表头
        header = "| Agent |"
        separator = "|-------|"
        for bench, scope in benchmarks:
            col = f"{bench}/{scope}"
            header += f" {col} ASR | {col} TCR |"
            separator += "------:|------:|"

        lines = [header, separator]
        for agent in agents:
            row = f"| {agent} |"
            for bench, scope in benchmarks:
                m = lookup.get((agent, bench, scope))
                if m:
                    row += f" {m.asr:.2%} | {m.tcr:.2%} |"
                else:
                    row += " - | - |"
            lines.append(row)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 消融实验表
    # ------------------------------------------------------------------

    def generate_ablation_table(
        self,
        results: dict[str, list[EvalMetrics]],
    ) -> str:
        """生成消融实验 Markdown 表格。"""
        # 收集所有 benchmark 列
        benchmarks: list[tuple[str, str]] = []
        seen = set()
        for metrics_list in results.values():
            for m in metrics_list:
                key = (m.benchmark, m.scope)
                if key not in seen:
                    benchmarks.append(key)
                    seen.add(key)

        header = "| Variant |"
        separator = "|---------|"
        for bench, scope in benchmarks:
            col = f"{bench}/{scope}"
            header += f" {col} ASR | {col} TCR |"
            separator += "------:|------:|"

        lines = [header, separator]
        for variant, metrics_list in results.items():
            lookup = {(m.benchmark, m.scope): m for m in metrics_list}
            row = f"| {variant} |"
            for bench, scope in benchmarks:
                m = lookup.get((bench, scope))
                if m:
                    row += f" {m.asr:.2%} | {m.tcr:.2%} |"
                else:
                    row += " - | - |"
            lines.append(row)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 决策分布表
    # ------------------------------------------------------------------

    def generate_decision_table(self, results: list[EvalMetrics]) -> str:
        """生成决策分布 Markdown 表格。"""
        all_decisions = set()
        for m in results:
            all_decisions.update(m.decision_counts.keys())
        decisions = sorted(all_decisions) if all_decisions else ["ALLOW", "DENY", "MODIFY", "CONFIRM"]

        header = "| Agent | Benchmark |"
        separator = "|-------|-----------|"
        for d in decisions:
            header += f" {d} |"
            separator += "-----:|"

        lines = [header, separator]
        for m in results:
            row = f"| {m.agent} | {m.benchmark}/{m.scope} |"
            for d in decisions:
                row += f" {m.decision_counts.get(d, 0)} |"
            lines.append(row)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 完整报告
    # ------------------------------------------------------------------

    def generate_full_report(
        self,
        eval_results: list[EvalMetrics],
        ablation_results: dict[str, list[EvalMetrics]] | None = None,
    ) -> Path:
        """生成完整 Markdown 报告。"""
        sections = []
        sections.append("# IntentGuard 评测报告\n")

        sections.append("## 1. Agent × Benchmark 对比\n")
        sections.append(self.generate_comparison_table(eval_results))

        sections.append("\n## 2. 决策分布\n")
        sections.append(self.generate_decision_table(eval_results))

        if ablation_results:
            sections.append("\n## 3. 消融实验\n")
            sections.append(self.generate_ablation_table(ablation_results))

        report = "\n".join(sections) + "\n"
        report_path = self._output_dir / "eval_report.md"
        report_path.write_text(report, encoding="utf-8")

        # 同时保存 JSON
        json_path = self._output_dir / "eval_report.json"
        payload: dict = {
            "eval_results": [m.to_dict() for m in eval_results],
        }
        if ablation_results:
            payload["ablation_results"] = {
                k: [m.to_dict() for m in v]
                for k, v in ablation_results.items()
            }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        print(f"[REPORT] Markdown: {report_path}")
        print(f"[REPORT] JSON: {json_path}")
        return report_path
