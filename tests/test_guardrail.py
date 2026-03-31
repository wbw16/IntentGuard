from __future__ import annotations

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch, PropertyMock

from runtime.intent_schema import IntentDeclaration
from guardrail import (
    CrossValidationResult,
    DecisionType,
    DimensionScore,
    GuardrailDecision,
    GuardrailMiddleware,
    ModifySubtype,
    PolicyMatch,
)
from guardrail.guard_model_adapter import (
    build_cross_validation_prompt,
    build_history_summary,
    parse_cross_validation_response,
)
from guardrail.cross_validator import CrossValidator
from guardrail.policy_engine import PolicyEngine
from guardrail.decision_maker import DecisionMaker
from guardrail.audit_logger import AuditLogger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_intent(**overrides) -> IntentDeclaration:
    defaults = dict(
        action_type="read",
        target_resource="/tmp/test.txt",
        operation_description="Read test file",
        data_source="user_input",
        data_destination="return_to_user",
        user_instruction_basis="user asked to read the file",
        expected_side_effects="none",
        preceding_dependency="none",
    )
    defaults.update(overrides)
    return IntentDeclaration(**defaults)


def _good_guard_response() -> str:
    return json.dumps({
        "intent_vs_params": {"score": 0.95, "contradictions": [], "evidence": "matches"},
        "intent_vs_user_query": {"score": 0.9, "contradictions": [], "evidence": "consistent"},
        "intent_vs_history": {"score": 0.85, "contradictions": [], "evidence": "logical"},
        "holistic": {"score": 0.9, "contradictions": [], "evidence": "all good"},
    })


def _bad_guard_response() -> str:
    return json.dumps({
        "intent_vs_params": {"score": 0.1, "contradictions": ["param mismatch"], "evidence": "bad"},
        "intent_vs_user_query": {"score": 0.2, "contradictions": ["scope exceeded"], "evidence": "bad"},
        "intent_vs_history": {"score": 0.15, "contradictions": ["sudden change"], "evidence": "bad"},
        "holistic": {"score": 0.15, "contradictions": ["overall inconsistent"], "evidence": "bad"},
    })


class FakeGuardModel:
    """Mock guard model that returns preset responses."""

    def __init__(self, response: str = ""):
        self.response = response
        self.model_type = "api"
        self.invoke_calls: list[list[dict]] = []

    def _invoke_model(self, messages, *, json_format=False):
        self.invoke_calls.append(messages)
        return self.response


# ---------------------------------------------------------------------------
# Tests: guard_model_adapter
# ---------------------------------------------------------------------------


class TestGuardModelAdapter(unittest.TestCase):
    def test_build_prompt_contains_all_context(self):
        intent = _make_intent()
        messages = build_cross_validation_prompt(
            intent, "read_file", {"path": "/tmp/test.txt"},
            "read the file", [{"role": "user", "content": "read the file"}],
            "read_file: reads a file",
        )
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("cross-validate", messages[0]["content"])
        user_content = messages[1]["content"]
        self.assertIn("read the file", user_content)
        self.assertIn("read_file", user_content)
        self.assertIn("/tmp/test.txt", user_content)

    def test_build_history_summary_truncates(self):
        history = [{"role": "assistant", "content": f"step {i}"} for i in range(20)]
        summary = build_history_summary(history, max_entries=5)
        self.assertEqual(summary.count("[assistant]"), 5)

    def test_build_history_summary_empty(self):
        self.assertEqual(build_history_summary([]), "(no prior actions)")

    def test_parse_good_response(self):
        result = parse_cross_validation_response(_good_guard_response())
        self.assertFalse(result.degraded)
        self.assertAlmostEqual(result.holistic_score, 0.9)
        self.assertAlmostEqual(result.intent_vs_params.score, 0.95)

    def test_parse_bad_json_returns_degraded(self):
        result = parse_cross_validation_response("not json at all")
        self.assertTrue(result.degraded)
        self.assertAlmostEqual(result.holistic_score, 0.0)

    def test_parse_non_dict_returns_degraded(self):
        result = parse_cross_validation_response('"just a string"')
        self.assertTrue(result.degraded)


# ---------------------------------------------------------------------------
# Tests: CrossValidator
# ---------------------------------------------------------------------------


class TestCrossValidator(unittest.TestCase):
    def test_consistent_intent_produces_high_scores(self):
        guard = FakeGuardModel(_good_guard_response())
        cv = CrossValidator(guard)
        result = cv.validate(
            _make_intent(), "read_file", {"path": "/tmp/test.txt"},
            "read the file", [], "",
        )
        self.assertFalse(result.degraded)
        self.assertGreaterEqual(result.holistic_score, 0.8)
        self.assertEqual(len(guard.invoke_calls), 1)

    def test_contradictory_intent_produces_low_scores(self):
        guard = FakeGuardModel(_bad_guard_response())
        cv = CrossValidator(guard)
        result = cv.validate(
            _make_intent(), "delete_file", {"path": "/etc/passwd"},
            "read the file", [], "",
        )
        self.assertFalse(result.degraded)
        self.assertLessEqual(result.holistic_score, 0.3)

    def test_model_exception_returns_degraded(self):
        guard = FakeGuardModel()
        guard._invoke_model = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("fail"))
        cv = CrossValidator(guard)
        result = cv.validate(_make_intent(), "t", {}, "q", [], "")
        self.assertTrue(result.degraded)


# ---------------------------------------------------------------------------
# Tests: PolicyEngine
# ---------------------------------------------------------------------------


class TestPolicyEngine(unittest.TestCase):
    def test_data_exfiltration_rule_matches(self):
        engine = PolicyEngine()
        intent = _make_intent(
            data_source="prior_tool_output",
            data_destination="external_service",
        )
        matches = engine.evaluate(intent)
        names = [m.rule_name for m in matches]
        self.assertIn("data_exfiltration_pattern", names)
        # highest priority rule first
        self.assertEqual(matches[0].effect, "deny")

    def test_read_only_safe_rule_matches(self):
        engine = PolicyEngine()
        intent = _make_intent(action_type="read", data_destination="return_to_user")
        matches = engine.evaluate(intent)
        names = [m.rule_name for m in matches]
        self.assertIn("read_only_safe", names)

    def test_unknown_intent_triggers_deny(self):
        engine = PolicyEngine()
        intent = _make_intent(target_resource="unknown")
        matches = engine.evaluate(intent)
        names = [m.rule_name for m in matches]
        self.assertIn("unknown_intent_fields", names)

    def test_no_rules_match_returns_empty(self):
        engine = PolicyEngine()
        intent = _make_intent(
            action_type="modify",
            data_destination="local_storage",
            data_source="user_input",
            target_resource="/tmp/safe.txt",
        )
        matches = engine.evaluate(intent)
        self.assertEqual(len(matches), 0)


# ---------------------------------------------------------------------------
# Tests: DecisionMaker
# ---------------------------------------------------------------------------


class TestDecisionMaker(unittest.TestCase):
    def test_high_score_no_policy_returns_allow(self):
        dm = DecisionMaker()
        cr = CrossValidationResult(
            holistic=DimensionScore(score=0.9),
        )
        decision = dm.decide(cr, [])
        self.assertEqual(decision.decision_type, DecisionType.ALLOW)

    def test_low_score_returns_deny(self):
        dm = DecisionMaker()
        cr = CrossValidationResult(
            holistic=DimensionScore(score=0.2, contradictions=["bad"]),
        )
        decision = dm.decide(cr, [])
        self.assertEqual(decision.decision_type, DecisionType.DENY)

    def test_policy_deny_overrides_high_score(self):
        dm = DecisionMaker()
        cr = CrossValidationResult(holistic=DimensionScore(score=0.95))
        policy = [PolicyMatch(rule_name="exfil", effect="deny", priority=200)]
        decision = dm.decide(cr, policy)
        self.assertEqual(decision.decision_type, DecisionType.DENY)

    def test_policy_allow_overrides_low_score(self):
        dm = DecisionMaker()
        cr = CrossValidationResult(holistic=DimensionScore(score=0.1))
        policy = [PolicyMatch(rule_name="safe", effect="allow", priority=50)]
        decision = dm.decide(cr, policy)
        self.assertEqual(decision.decision_type, DecisionType.ALLOW)

    def test_mid_score_returns_confirm(self):
        dm = DecisionMaker()
        cr = CrossValidationResult(holistic=DimensionScore(score=0.4))
        decision = dm.decide(cr, [])
        self.assertEqual(decision.decision_type, DecisionType.CONFIRM)

    def test_modify_range_score(self):
        dm = DecisionMaker()
        cr = CrossValidationResult(holistic=DimensionScore(score=0.65))
        decision = dm.decide(cr, [])
        self.assertEqual(decision.decision_type, DecisionType.MODIFY)


# ---------------------------------------------------------------------------
# Tests: AuditLogger
# ---------------------------------------------------------------------------


class TestAuditLogger(unittest.TestCase):
    def test_writes_jsonl_line(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(output_dir=tmpdir, enabled=True)
            intent = _make_intent()
            cr = CrossValidationResult(holistic=DimensionScore(score=0.9))
            decision = GuardrailDecision(decision_type=DecisionType.ALLOW, reason="ok")
            record = logger.log(intent, "read_file", {"path": "/tmp"}, "read", cr, [], decision)
            self.assertIn("call_id", record)
            self.assertIn("timestamp", record)
            log_file = os.path.join(tmpdir, "audit.jsonl")
            self.assertTrue(os.path.exists(log_file))
            with open(log_file) as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 1)
            parsed = json.loads(lines[0])
            self.assertEqual(parsed["tool_name"], "read_file")

    def test_disabled_logger_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(output_dir=tmpdir, enabled=False)
            intent = _make_intent()
            cr = CrossValidationResult()
            decision = GuardrailDecision()
            logger.log(intent, "t", {}, "q", cr, [], decision)
            log_file = os.path.join(tmpdir, "audit.jsonl")
            self.assertFalse(os.path.exists(log_file))


# ---------------------------------------------------------------------------
# Tests: GuardrailMiddleware (integration)
# ---------------------------------------------------------------------------


class TestGuardrailMiddleware(unittest.TestCase):
    def test_allow_flow(self):
        guard = FakeGuardModel(_good_guard_response())
        with tempfile.TemporaryDirectory() as tmpdir:
            mw = GuardrailMiddleware(guard, audit_dir=tmpdir)
            intent = _make_intent()
            decision = mw.evaluate(intent, "read_file", {"path": "/tmp/x"}, "read file", [])
            self.assertEqual(decision.decision_type, DecisionType.ALLOW)
            self.assertIsNotNone(decision.cross_validation)
            self.assertFalse(decision.cross_validation.degraded)

    def test_deny_flow(self):
        guard = FakeGuardModel(_bad_guard_response())
        with tempfile.TemporaryDirectory() as tmpdir:
            mw = GuardrailMiddleware(guard, audit_dir=tmpdir)
            intent = _make_intent(
                action_type="modify",
                data_destination="local_storage",
            )
            decision = mw.evaluate(intent, "delete_file", {"path": "/etc/passwd"}, "read file", [])
            self.assertEqual(decision.decision_type, DecisionType.DENY)

    def test_policy_override_deny(self):
        """Even with good cross-validation, exfiltration pattern triggers deny."""
        guard = FakeGuardModel(_good_guard_response())
        with tempfile.TemporaryDirectory() as tmpdir:
            mw = GuardrailMiddleware(guard, audit_dir=tmpdir)
            intent = _make_intent(
                data_source="prior_tool_output",
                data_destination="external_service",
            )
            decision = mw.evaluate(intent, "send_email", {}, "send data", [])
            self.assertEqual(decision.decision_type, DecisionType.DENY)


if __name__ == "__main__":
    unittest.main()
