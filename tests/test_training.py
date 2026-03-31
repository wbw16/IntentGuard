from __future__ import annotations

import json
import os
import tempfile
import unittest

from training.label_schema import (
    AttackScenario,
    AttackType,
    DecisionLabel,
    DeceptionStrategy,
    ExecutionTrace,
    TraceStep,
    TrainingSample,
    compute_distribution,
    validate_sample,
)
from training.data_collector import DataCollector
from training.sample_constructor import SampleConstructor
from training.deception_augmentor import DeceptionAugmentor
from training.train_guard import GuardTrainer


# ---------------------------------------------------------------------------
# Tests: label_schema
# ---------------------------------------------------------------------------


class TestLabelSchema(unittest.TestCase):
    def test_training_sample_roundtrip(self):
        sample = TrainingSample(
            sample_id="test_001",
            user_query="read the file",
            intent_declaration={"action_type": "read", "target_resource": "/tmp/x"},
            tool_name="read_file",
            tool_params={"path": "/tmp/x"},
            decision_label=DecisionLabel.ALLOW,
            risk_level=0.0,
            reason="normal call",
            source="agentharm",
            scenario_id="s1",
            attack_type=AttackType.NONE,
        )
        d = sample.to_dict()
        restored = TrainingSample.from_dict(d)
        self.assertEqual(restored.sample_id, "test_001")
        self.assertEqual(restored.decision_label, DecisionLabel.ALLOW)
        self.assertEqual(restored.tool_name, "read_file")
        self.assertEqual(restored.attack_type, AttackType.NONE)

    def test_validate_sample_catches_missing_fields(self):
        sample = TrainingSample()
        errors = validate_sample(sample)
        self.assertIn("missing sample_id", errors)
        self.assertIn("missing user_query", errors)
        self.assertIn("missing tool_name", errors)

    def test_compute_distribution(self):
        samples = [
            TrainingSample(decision_label=DecisionLabel.ALLOW, attack_type=AttackType.NONE),
            TrainingSample(decision_label=DecisionLabel.DENY, attack_type=AttackType.OPI),
            TrainingSample(decision_label=DecisionLabel.DENY, attack_type=AttackType.DPI,
                           is_deceptive_intent=True),
        ]
        dist = compute_distribution(samples)
        self.assertEqual(dist["total"], 3)
        self.assertEqual(dist["decision_distribution"]["ALLOW"], 1)
        self.assertEqual(dist["decision_distribution"]["DENY"], 2)
        self.assertEqual(dist["deceptive_intent_count"], 1)

    def test_attack_scenario_to_dict(self):
        s = AttackScenario(
            scenario_id="test",
            source="asb",
            query="do something",
            tools=["tool_a"],
            attack_type=AttackType.OPI,
        )
        d = s.to_dict()
        self.assertEqual(d["attack_type"], "OPI")
        self.assertEqual(d["source"], "asb")

    def test_execution_trace_to_dict(self):
        trace = ExecutionTrace(
            scenario_id="s1",
            agent_strategy="react",
            steps=[TraceStep(step_index=0, tool_name="t1")],
            was_attacked=True,
            attack_succeeded=False,
        )
        d = trace.to_dict()
        self.assertEqual(len(d["steps"]), 1)
        self.assertTrue(d["was_attacked"])


# ---------------------------------------------------------------------------
# Tests: DataCollector
# ---------------------------------------------------------------------------


class TestDataCollector(unittest.TestCase):
    def test_collect_agentharm_harmful(self):
        collector = DataCollector()
        scenarios = collector.collect_agentharm("harmful")
        # 数据文件存在则应有结果
        if scenarios:
            self.assertTrue(all(s.source == "agentharm" for s in scenarios))
            self.assertTrue(all(s.attack_type == AttackType.HARMFUL for s in scenarios))
            self.assertTrue(all(s.query for s in scenarios))

    def test_collect_agentharm_benign(self):
        collector = DataCollector()
        scenarios = collector.collect_agentharm("benign")
        if scenarios:
            self.assertTrue(all(s.attack_type == AttackType.NONE for s in scenarios))

    def test_collect_asb(self):
        collector = DataCollector()
        scenarios = collector.collect_asb("OPI")
        if scenarios:
            self.assertTrue(all(s.source == "asb" for s in scenarios))
            self.assertTrue(all(s.attack_type == AttackType.OPI for s in scenarios))

    def test_collect_all_returns_list(self):
        collector = DataCollector()
        scenarios = collector.collect_all()
        self.assertIsInstance(scenarios, list)


# ---------------------------------------------------------------------------
# Tests: SampleConstructor
# ---------------------------------------------------------------------------


class TestSampleConstructor(unittest.TestCase):
    def test_construct_from_benign_trace(self):
        sc = SampleConstructor()
        scenario = AttackScenario(
            scenario_id="benign_1",
            source="test",
            query="read file",
            attack_type=AttackType.NONE,
        )
        trace = ExecutionTrace(
            scenario_id="benign_1",
            agent_strategy="react",
            steps=[
                TraceStep(step_index=0, tool_name="read_file",
                          tool_params={"path": "/tmp/x"},
                          intent={"action_type": "read"}),
            ],
            was_attacked=False,
            attack_succeeded=False,
        )
        samples = sc.construct_from_trace(trace, scenario)
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].decision_label, DecisionLabel.ALLOW)
        self.assertAlmostEqual(samples[0].risk_level, 0.0)

    def test_construct_from_attack_trace(self):
        sc = SampleConstructor()
        scenario = AttackScenario(
            scenario_id="attack_1",
            source="test",
            query="do task",
            attack_type=AttackType.OPI,
            expected_harmful_tool="evil_tool",
        )
        trace = ExecutionTrace(
            scenario_id="attack_1",
            agent_strategy="react",
            steps=[
                TraceStep(step_index=0, tool_name="safe_tool"),
                TraceStep(step_index=1, tool_name="evil_tool"),
            ],
            was_attacked=True,
            attack_succeeded=True,
        )
        samples = sc.construct_from_trace(trace, scenario)
        self.assertEqual(len(samples), 2)
        # evil_tool step should be DENY
        evil_sample = [s for s in samples if s.tool_name == "evil_tool"][0]
        self.assertEqual(evil_sample.decision_label, DecisionLabel.DENY)
        self.assertAlmostEqual(evil_sample.risk_level, 1.0)


# ---------------------------------------------------------------------------
# Tests: DeceptionAugmentor
# ---------------------------------------------------------------------------


class TestDeceptionAugmentor(unittest.TestCase):
    def test_augment_adds_deceptive_variants(self):
        augmentor = DeceptionAugmentor(llm_client=None)
        samples = [
            TrainingSample(
                sample_id="atk_1",
                user_query="do task",
                tool_name="evil_tool",
                tool_params={"target": "secret"},
                intent_declaration={"action_type": "execute"},
                decision_label=DecisionLabel.DENY,
                risk_level=1.0,
                reason="attack",
            ),
            TrainingSample(
                sample_id="safe_1",
                user_query="read file",
                tool_name="read_file",
                decision_label=DecisionLabel.ALLOW,
                reason="safe",
            ),
        ]
        augmented = augmentor.augment(samples)
        # Should have original samples + deception variants for the DENY sample
        self.assertGreater(len(augmented), len(samples))
        deceptive = [s for s in augmented if s.is_deceptive_intent]
        self.assertGreater(len(deceptive), 0)
        self.assertTrue(all(s.decision_label == DecisionLabel.DENY for s in deceptive))

    def test_disabled_augmentor_returns_original(self):
        augmentor = DeceptionAugmentor(llm_client=None)
        augmentor._enabled = False
        samples = [TrainingSample(sample_id="x", decision_label=DecisionLabel.DENY)]
        result = augmentor.augment(samples)
        self.assertEqual(len(result), 1)

    def test_rule_based_fake_intent(self):
        augmentor = DeceptionAugmentor(llm_client=None)
        sample = TrainingSample(
            tool_name="delete_file",
            tool_params={"path": "/etc/passwd"},
            intent_declaration={"action_type": "delete"},
        )
        fake = augmentor._rule_based_fake_intent(sample, "understate_risk")
        self.assertEqual(fake["action_type"], "read")
        self.assertEqual(fake["expected_side_effects"], "none")


# ---------------------------------------------------------------------------
# Tests: GuardTrainer
# ---------------------------------------------------------------------------


class TestGuardTrainer(unittest.TestCase):
    def test_save_and_load_samples(self):
        trainer = GuardTrainer()
        samples = [
            TrainingSample(
                sample_id="t1",
                user_query="test",
                tool_name="tool",
                intent_declaration={"action_type": "read"},
                decision_label=DecisionLabel.ALLOW,
                reason="ok",
            ),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "samples.jsonl")
            trainer.save_samples(samples, path)
            loaded = trainer.load_samples(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].sample_id, "t1")

    def test_validate_dataset(self):
        trainer = GuardTrainer()
        samples = [
            TrainingSample(sample_id="ok", user_query="q", tool_name="t",
                           intent_declaration={"a": 1}, reason="r"),
            TrainingSample(),  # invalid: missing everything
        ]
        result = trainer.validate_dataset(samples)
        self.assertEqual(result["invalid_samples"], 1)
        self.assertIn("total", result["distribution"])

    def test_prepare_sft_data(self):
        trainer = GuardTrainer()
        samples = [
            TrainingSample(
                sample_id="s1",
                user_query="read file",
                tool_name="read_file",
                tool_params={"path": "/tmp/x"},
                intent_declaration={"action_type": "read"},
                decision_label=DecisionLabel.ALLOW,
                risk_level=0.0,
                reason="normal",
            ),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sft.jsonl")
            trainer.prepare_sft_data(samples, path)
            with open(path) as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 1)
            entry = json.loads(lines[0])
            self.assertIn("messages", entry)
            self.assertEqual(len(entry["messages"]), 3)
            self.assertEqual(entry["messages"][0]["role"], "system")

    def test_train_dry_run(self):
        trainer = GuardTrainer()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal SFT data
            sft_path = os.path.join(tmpdir, "sft.jsonl")
            with open(sft_path, "w") as f:
                f.write('{"messages": []}\n')
            result = trainer.train(sft_path)
            # Without GPU, should return dry_run
            self.assertIn(result["status"], ("dry_run", "error"))


if __name__ == "__main__":
    unittest.main()
