from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evaluation.metrics import (
    EvalMetrics,
    compute_metrics_from_meta,
    load_and_compute,
    _extract_attack_tool,
    _tool_was_called,
    _task_completed,
    _extract_decisions,
)
from evaluation.eval_runner import EvalRunner
from evaluation.report_generator import ReportGenerator


class TestEvalMetrics(unittest.TestCase):

    def test_asr_zero_samples(self):
        m = EvalMetrics()
        self.assertEqual(m.asr, 0.0)

    def test_asr_calculation(self):
        m = EvalMetrics(total_samples=10, attack_success_count=3)
        self.assertAlmostEqual(m.asr, 0.3)

    def test_tcr_calculation(self):
        m = EvalMetrics(total_samples=10, task_complete_count=8)
        self.assertAlmostEqual(m.tcr, 0.8)

    def test_fpr_calculation(self):
        m = EvalMetrics(benign_total=20, false_positive_count=4)
        self.assertAlmostEqual(m.fpr, 0.2)

    def test_fpr_zero_benign(self):
        m = EvalMetrics(benign_total=0, false_positive_count=0)
        self.assertEqual(m.fpr, 0.0)

    def test_avg_latency(self):
        m = EvalMetrics(total_samples=5, total_latency=10.0)
        self.assertAlmostEqual(m.avg_latency, 2.0)

    def test_deception_detection_rate(self):
        m = EvalMetrics(deception_total=10, deception_detected=7)
        self.assertAlmostEqual(m.deception_detection_rate, 0.7)

    def test_to_dict(self):
        m = EvalMetrics(
            agent="react", benchmark="agentharm", scope="harmful",
            total_samples=10, attack_success_count=2, task_complete_count=8,
        )
        d = m.to_dict()
        self.assertEqual(d["agent"], "react")
        self.assertAlmostEqual(d["asr"], 0.2)
        self.assertAlmostEqual(d["tcr"], 0.8)


class TestMetricHelpers(unittest.TestCase):

    def test_extract_attack_tool_asb(self):
        meta = {"attack_tool": {"Attacker Tool": "evil_tool"}}
        self.assertEqual(_extract_attack_tool(meta), "evil_tool")

    def test_extract_attack_tool_agentdojo(self):
        meta = {"injection_name": "injection_bill_text"}
        self.assertEqual(_extract_attack_tool(meta), "injection_bill_text")

    def test_tool_was_called(self):
        self.assertTrue(_tool_was_called("-- running evil_tool {}", "evil_tool"))
        self.assertFalse(_tool_was_called("-- running safe_tool {}", "evil_tool"))
        self.assertFalse(_tool_was_called("", "evil_tool"))

    def test_task_completed(self):
        self.assertTrue(_task_completed("Final Answer: done", []))
        self.assertTrue(_task_completed("some logs", [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "thinking"},
            {"role": "assistant", "content": "done"},
        ]))
        self.assertFalse(_task_completed("", []))

    def test_extract_decisions(self):
        logs = "[GUARDRAIL] Decision: ALLOW\n[GUARDRAIL] Decision: DENY"
        decisions = _extract_decisions(logs)
        self.assertEqual(decisions, ["ALLOW", "DENY"])

    def test_extract_decisions_dataclass_format(self):
        logs = "GuardrailDecision(type=MODIFY, reason=...)"
        decisions = _extract_decisions(logs)
        self.assertEqual(decisions, ["MODIFY"])


class TestComputeMetricsFromMeta(unittest.TestCase):

    def test_basic(self):
        meta = [
            {
                "logs": "-- running evil_tool {}\nFinal Answer: done",
                "messages": [{"role": "assistant", "content": "done"}],
                "meta_sample": {"attack_tool": {"Attacker Tool": "evil_tool"}},
            },
            {
                "logs": "-- running safe_tool {}\nFinal Answer: ok",
                "messages": [{"role": "assistant", "content": "ok"}],
                "meta_sample": {"attack_tool": {"Attacker Tool": "evil_tool"}},
            },
        ]
        m = compute_metrics_from_meta(meta, agent="react", benchmark="asb", scope="OPI")
        self.assertEqual(m.total_samples, 2)
        self.assertEqual(m.attack_success_count, 1)
        self.assertEqual(m.task_complete_count, 2)

    def test_empty_meta(self):
        m = compute_metrics_from_meta([])
        self.assertEqual(m.total_samples, 0)
        self.assertEqual(m.asr, 0.0)


class TestLoadAndCompute(unittest.TestCase):

    def test_missing_file(self):
        m = load_and_compute(Path("/nonexistent/path.json"))
        self.assertEqual(m.total_samples, 0)

    def test_from_file(self):
        meta = [{"logs": "Final Answer: x", "messages": [], "meta_sample": {}}]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(meta, f)
            f.flush()
            m = load_and_compute(Path(f.name), agent="test")
        self.assertEqual(m.total_samples, 1)


class TestEvalRunnerBuildSpecs(unittest.TestCase):

    def test_build_specs_default(self):
        runner = EvalRunner()
        specs = runner.build_run_specs()
        self.assertGreater(len(specs), 0)
        agents = {s.agent for s in specs}
        benchmarks = {s.benchmark for s in specs}
        self.assertIn("react", agents)
        self.assertIn("intentguard", agents)
        self.assertIn("agentharm", benchmarks)
        self.assertIn("asb", benchmarks)

    def test_build_specs_filtered(self):
        runner = EvalRunner()
        specs = runner.build_run_specs(agents=["react"], benchmarks=["agentharm"])
        self.assertTrue(all(s.agent == "react" for s in specs))
        self.assertTrue(all(s.benchmark == "agentharm" for s in specs))


class TestReportGenerator(unittest.TestCase):

    def test_comparison_table(self):
        results = [
            EvalMetrics(agent="react", benchmark="agentharm", scope="harmful",
                        total_samples=10, attack_success_count=5, task_complete_count=8),
            EvalMetrics(agent="intentguard", benchmark="agentharm", scope="harmful",
                        total_samples=10, attack_success_count=1, task_complete_count=9),
        ]
        reporter = ReportGenerator(output_dir=tempfile.mkdtemp())
        table = reporter.generate_comparison_table(results)
        self.assertIn("react", table)
        self.assertIn("intentguard", table)
        self.assertIn("50.00%", table)
        self.assertIn("10.00%", table)

    def test_ablation_table(self):
        results = {
            "full": [EvalMetrics(agent="intentguard", benchmark="agentharm", scope="harmful",
                                 total_samples=10, attack_success_count=1)],
            "no_intent": [EvalMetrics(agent="intentguard", benchmark="agentharm", scope="harmful",
                                      total_samples=10, attack_success_count=5)],
        }
        reporter = ReportGenerator(output_dir=tempfile.mkdtemp())
        table = reporter.generate_ablation_table(results)
        self.assertIn("full", table)
        self.assertIn("no_intent", table)

    def test_full_report(self):
        results = [
            EvalMetrics(agent="react", benchmark="asb", scope="OPI",
                        total_samples=5, attack_success_count=2, task_complete_count=3),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = ReportGenerator(output_dir=tmpdir)
            path = reporter.generate_full_report(results)
            self.assertTrue(path.exists())
            content = path.read_text()
            self.assertIn("Agent × Benchmark", content)
            # JSON 也应该存在
            json_path = Path(tmpdir) / "eval_report.json"
            self.assertTrue(json_path.exists())


if __name__ == "__main__":
    unittest.main()
