from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

from phase0.baselines import run_phase0_baselines
from phase0.common import load_repo_env
from phase0.readiness import collect_phase0_readiness
from phase0.scoring import generate_metrics_summary
from runtime.modeling import RuntimeModelConfig, StandaloneGuardian


class CompatibilityTests(unittest.TestCase):
    def test_standalone_namespace_imports(self) -> None:
        import standalone_agent_env
        import standalone_agent_env.agents.react_agent
        import standalone_agent_env.processors.agentharm
        import standalone_agent_env.runtime.core

        self.assertTrue(hasattr(standalone_agent_env, "agents"))
        self.assertTrue(hasattr(standalone_agent_env, "runtime"))
        self.assertTrue(hasattr(standalone_agent_env, "processors"))


class ReadinessTests(unittest.TestCase):
    def _write_env(self, path: Path, api_key: str) -> None:
        path.write_text(
            "\n".join(
                [
                    "STANDALONE_REACT_MODEL_NAME=gpt-4o-mini",
                    f"STANDALONE_REACT_API_KEY={api_key}",
                    "STANDALONE_REACT_API_BASE=http://localhost:8000/v1",
                    "STANDALONE_SEC_REACT_MODEL_NAME=gpt-4o-mini",
                    f"STANDALONE_SEC_REACT_API_KEY={api_key}",
                    "STANDALONE_SEC_REACT_API_BASE=http://localhost:8000/v1",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def test_collect_phase0_readiness_passes_with_valid_temp_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            env_file = temp_path / ".env"
            self._write_env(env_file, api_key="test-key")

            with patch.dict(os.environ, {}, clear=True):
                report = collect_phase0_readiness(output_root=temp_path / "outputs" / "baseline", env_file=env_file)

        self.assertTrue(report["ok"])
        self.assertEqual(report["summary"]["failed"], 0)

    def test_collect_phase0_readiness_reports_missing_model_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            env_file = temp_path / ".env"
            self._write_env(env_file, api_key="REPLACE_ME")

            with patch.dict(os.environ, {}, clear=True):
                report = collect_phase0_readiness(output_root=temp_path / "outputs" / "baseline", env_file=env_file)

        self.assertFalse(report["ok"])
        failing_checks = {check["id"]: check for check in report["checks"] if check["status"] == "fail"}
        self.assertIn("model_config", failing_checks)

    def test_load_repo_env_expands_variable_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "DEFAULT_API_BASE=https://example.com/v1",
                        "DEFAULT_API_KEY=test-key",
                        "STANDALONE_REACT_API_BASE=${DEFAULT_API_BASE}",
                        "STANDALONE_REACT_API_KEY=${DEFAULT_API_KEY}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                values = load_repo_env(env_file)

        self.assertEqual(values["STANDALONE_REACT_API_BASE"], "https://example.com/v1")
        self.assertEqual(values["STANDALONE_REACT_API_KEY"], "test-key")


class BaselineRunnerTests(unittest.TestCase):
    def test_run_phase0_baselines_resumes_partial_artifact_and_skips_complete_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "outputs" / "baseline"
            artifact_path = output_root / "agentharm" / "react" / "harmful" / "meta_data.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text('[{"messages": [], "meta_sample": {"target_functions": ["send_email"]}}]\n', encoding="utf-8")

            class FakeProcessor:
                def __init__(self, agent, output_save_dir, subtask):
                    self.output_save_dir = Path(output_save_dir)

                def run(self):
                    meta_path = self.output_save_dir / "meta_data.json"
                    existing = []
                    if meta_path.exists():
                        import json

                        existing = json.loads(meta_path.read_text(encoding="utf-8"))
                    existing.append({"messages": [], "meta_sample": {"target_functions": ["send_email"]}})
                    meta_path.write_text(__import__("json").dumps(existing) + "\n", encoding="utf-8")
                    return existing

            fake_builder_calls = []

            def fake_get_agent_builder(agent_name):
                fake_builder_calls.append(agent_name)

                def _builder():
                    return object()

                return _builder

            with patch("phase0.baselines.expected_samples_for_spec", return_value=2), patch(
                "agents.get_agent_builder",
                side_effect=fake_get_agent_builder,
            ), patch(
                "standalone_agent_env.agents.get_agent_builder",
                side_effect=fake_get_agent_builder,
            ), patch(
                "processors.agentharm.AgentHarmProcessor",
                FakeProcessor,
            ), patch(
                "standalone_agent_env.processors.agentharm.AgentHarmProcessor",
                FakeProcessor,
            ):
                first_manifest = run_phase0_baselines(
                    output_root=output_root,
                    agents=["react"],
                    benchmarks=["agentharm"],
                    skip_readiness=True,
                )
                second_manifest = run_phase0_baselines(
                    output_root=output_root,
                    agents=["react"],
                    benchmarks=["agentharm"],
                    skip_readiness=True,
                )

        first_run = first_manifest["runs"][0]
        second_run = second_manifest["runs"][0]
        self.assertEqual(first_run["status"], "completed")
        self.assertTrue(first_run["resumed"])
        self.assertEqual(first_run["actual_samples_before"], 1)
        self.assertEqual(first_run["actual_samples_after"], 2)
        self.assertEqual(second_run["status"], "skipped_complete")
        self.assertEqual(fake_builder_calls, ["react"])


class MetricsSummaryTests(unittest.TestCase):
    def test_generate_metrics_summary_marks_missing_artifacts_without_zero_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = generate_metrics_summary(
                output_root=Path(temp_dir) / "outputs" / "baseline",
                agents=["react"],
                benchmarks=["agentharm"],
            )

        self.assertEqual(len(summary["entries"]), 1)
        entry = summary["entries"][0]
        self.assertEqual(entry["status"], "missing")
        self.assertIsNone(entry["asr"])
        self.assertIsNone(entry["tcr"])

    def test_generate_metrics_summary_scores_proxy_metrics_for_both_benchmarks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir) / "outputs" / "baseline"

            agentharm_path = output_root / "agentharm" / "react" / "harmful" / "meta_data.json"
            agentharm_path.parent.mkdir(parents=True, exist_ok=True)
            agentharm_path.write_text(
                (
                    '[{"messages": [{"role": "assistant", "content": "Thought\\nAction: send_email\\nAction Input: {\\"to\\": \\"a@example.com\\"}"}], '
                    '"meta_sample": {"target_functions": ["send_email"]}}]\n'
                ),
                encoding="utf-8",
            )

            asb_path = output_root / "asb" / "react" / "opi" / "meta_data.json"
            asb_path.parent.mkdir(parents=True, exist_ok=True)
            asb_path.write_text(
                (
                    '[{"messages": ['
                    '{"role": "assistant", "content": "Action: attack_tool\\nAction Input: {}"}, '
                    '{"role": "assistant", "content": "Action: normal_tool\\nAction Input: {}"}], '
                    '"meta_sample": {"attack_tool": {"Attacker Tool": "attack_tool"}, "normal_tools": [{"Tool Name": "normal_tool"}]}}]\n'
                ),
                encoding="utf-8",
            )

            agentharm_summary = generate_metrics_summary(
                output_root=output_root,
                agents=["react"],
                benchmarks=["agentharm"],
            )
            asb_summary = generate_metrics_summary(
                output_root=output_root,
                agents=["react"],
                benchmarks=["asb"],
            )

        self.assertEqual(agentharm_summary["entries"][0]["status"], "success")
        self.assertEqual(agentharm_summary["entries"][0]["asr"], 1.0)
        self.assertEqual(agentharm_summary["entries"][0]["tcr"], 1.0)
        self.assertEqual(asb_summary["entries"][0]["status"], "success")
        self.assertEqual(asb_summary["entries"][0]["asr"], 1.0)
        self.assertEqual(asb_summary["entries"][0]["tcr"], 1.0)


class GuardFallbackTests(unittest.TestCase):
    def test_unknown_guard_model_name_uses_default_template_and_parser(self) -> None:
        guardian = StandaloneGuardian(
            RuntimeModelConfig(
                model_name="mimo-v2-pro",
                model_type="api",
                api_base="https://example.com/v1",
                api_key="test-key",
            )
        )
        fake_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            "<malicious_user_request> no <\\malicious_user_request>\n"
                            "<being_attacked> no <\\being_attacked>\n"
                            "<harmfulness_rating> 0.0 <\\harmfulness_rating>"
                        )
                    )
                )
            ]
        )
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: fake_response,
                )
            )
        )

        with patch.object(StandaloneGuardian, "client", new_callable=PropertyMock, return_value=fake_client):
            result = guardian.get_judgment_res(
                {
                    "env_info": "Echo tool",
                    "user_request": "Echo phase0-ok",
                    "agent_action": {"interaction_history": [], "current_action": {"tool": "echo_tool"}},
                }
            )

        self.assertEqual(result["risk rating"], 0.0)


if __name__ == "__main__":
    unittest.main()
