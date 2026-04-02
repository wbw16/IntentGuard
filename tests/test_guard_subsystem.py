from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

from agents.react_firewall_agent import ReActFirewallAgent
from agents.sec_planexecute_agent import SecPlanExecuteAgent
from agents.sec_react_agent import SecReActAgent
from guard import GuardDecision, GuardEvaluationRequest, resolve_guard_config
from runtime.factory import create_guard_from_env
from runtime.modeling import RuntimeModelConfig, StandaloneGuardian


class GuardConfigTests(unittest.TestCase):
    def test_standalone_namespace_exposes_guard_package(self) -> None:
        import standalone_agent_env
        import standalone_agent_env.guard

        self.assertTrue(hasattr(standalone_agent_env, "guard"))

    def test_resolve_guard_config_preserves_primary_defaults_and_overrides(self) -> None:
        primary = RuntimeModelConfig(
            model_name="gpt-4o-mini",
            model_type="api",
            model_path="",
            api_base="https://primary.example/v1",
            api_key="primary-key",
            temperature=0.2,
            top_p=0.8,
            max_tokens=1024,
            timeout=30.0,
        )

        inherited = resolve_guard_config("STANDALONE_REACT", primary, environ={})
        self.assertEqual(inherited.model_config.model_name, "gpt-4o-mini")
        self.assertEqual(inherited.model_config.api_key, "primary-key")
        self.assertEqual(inherited.block_threshold, 0.5)

        overridden = resolve_guard_config(
            "STANDALONE_REACT",
            primary,
            environ={
                "STANDALONE_REACT_GUARD_MODEL_NAME": "shieldagent",
                "STANDALONE_REACT_GUARD_API_KEY": "guard-key",
                "STANDALONE_REACT_GUARD_TEMPERATURE": "0.0",
                "STANDALONE_REACT_GUARD_MAX_ATTEMPTS": "5",
                "STANDALONE_REACT_GUARD_BLOCK_THRESHOLD": "0.7",
            },
        )
        self.assertEqual(overridden.model_config.model_name, "shieldagent")
        self.assertEqual(overridden.model_config.api_key, "guard-key")
        self.assertEqual(overridden.model_config.temperature, 0.0)
        self.assertEqual(overridden.max_attempts, 5)
        self.assertEqual(overridden.block_threshold, 0.7)

    def test_create_guard_from_env_uses_shared_guard_subsystem(self) -> None:
        primary = RuntimeModelConfig(
            model_name="gpt-4o-mini",
            model_type="api",
            api_base="https://example.com/v1",
            api_key="test-key",
        )
        guard = create_guard_from_env("STANDALONE_REACT", primary)
        self.assertTrue(hasattr(guard, "review_tool_action"))
        self.assertTrue(hasattr(guard, "review_alignment"))


class GuardDecisionTests(unittest.TestCase):
    def _request(self) -> GuardEvaluationRequest:
        return GuardEvaluationRequest(
            user_request="Echo phase0-ok",
            interaction_history=[],
            current_action={"tool": "echo_tool"},
            current_action_description="Echo tool",
        )

    def test_tool_safety_review_normalizes_default_template_and_parser(self) -> None:
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
            decision = guardian.review_tool_action(self._request())

        self.assertTrue(decision.allowed)
        self.assertFalse(decision.degraded)
        self.assertEqual(decision.score, 0.0)
        self.assertEqual(decision.template_key, "qwen2.5-7b-instruct")
        self.assertEqual(decision.parser_key, "qwen2.5-7b-instruct")

    def test_tool_safety_review_returns_structured_degraded_decision(self) -> None:
        guardian = StandaloneGuardian(
            RuntimeModelConfig(
                model_name="gpt-4o-mini",
                model_type="api",
                api_base="https://example.com/v1",
                api_key="test-key",
            )
        )
        fake_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="unstructured guard output"))]
        )
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: fake_response,
                )
            )
        )

        with patch.object(StandaloneGuardian, "client", new_callable=PropertyMock, return_value=fake_client):
            decision = guardian.review_tool_action(self._request())

        self.assertTrue(decision.allowed)
        self.assertTrue(decision.degraded)
        self.assertIsNone(decision.score)
        self.assertEqual(decision.error, "unparsed_guard_output")
        self.assertEqual(decision.raw_output, "unstructured guard output")


class SequencedAgentCore:
    responses: list[str] = []

    def __init__(self, system: str = "", agentic_model=None):
        self.system = system
        self.agentic_model = agentic_model
        self.messages = []
        if system:
            self.messages.append({"role": "system", "content": system})

    def __call__(self, message: str, json_format: bool = False) -> str:
        if self.messages and self.messages[-1]["role"] == "user" and self.messages[-1]["content"] == message:
            result = type(self).responses.pop(0)
            self.messages.append({"role": "assistant", "content": result})
            return result

        self.messages.append({"role": "user", "content": message})
        result = type(self).responses.pop(0)
        self.messages.append({"role": "assistant", "content": result})
        return result


class FakeGuard:
    def __init__(
        self,
        *,
        tool_decision: GuardDecision | None = None,
        alignment_decision: GuardDecision | None = None,
    ):
        self.tool_decision = tool_decision
        self.alignment_decision = alignment_decision
        self.tool_requests: list[GuardEvaluationRequest] = []
        self.alignment_requests: list[GuardEvaluationRequest] = []

    def review_tool_action(self, request: GuardEvaluationRequest) -> GuardDecision:
        self.tool_requests.append(request)
        if self.tool_decision is None:
            raise AssertionError("tool_decision was not configured")
        return self.tool_decision

    def review_alignment(self, request: GuardEvaluationRequest) -> GuardDecision:
        self.alignment_requests.append(request)
        if self.alignment_decision is None:
            raise AssertionError("alignment_decision was not configured")
        return self.alignment_decision

    def call_tool(self, tool_name: str, arguments):
        raise AssertionError(f"secure agent should use GuardDecision interface, not legacy call_tool: {tool_name}")


class SecureAgentIntegrationTests(unittest.TestCase):
    def test_sec_react_blocks_before_tool_execution(self) -> None:
        guard = FakeGuard(
            tool_decision=GuardDecision(
                mode="tool_safety",
                allowed=False,
                reason="blocked",
                raw_output="blocked",
                score=1.0,
            )
        )
        tool_called = {"value": False}

        def send_email(**kwargs):
            tool_called["value"] = True
            return "sent"

        SequencedAgentCore.responses = [
            '(1) Thought: use tool\n(2) Action: send_email\n(3) Action Input: {"to": "a@example.com"}'
        ]
        agent = SecReActAgent(
            system_template="{available_tool_descriptions}\n{available_tool_names}",
            agentic_model=SimpleNamespace(model_type="api"),
            guard_model=guard,
            max_turns=1,
        )

        with patch("agents.sec_react_agent.AgentCore", SequencedAgentCore):
            logs, _, _ = agent.agent_invoke(
                query="send an email",
                available_tool_descriptions={"send_email": "send email"},
                available_tool_params={},
                known_actions={"send_email": send_email},
            )

        self.assertFalse(tool_called["value"])
        self.assertEqual(len(guard.tool_requests), 1)
        self.assertIn(" -- running send_email", logs)

    def test_sec_planexecute_allows_tool_execution_through_shared_guard_interface(self) -> None:
        guard = FakeGuard(
            tool_decision=GuardDecision(
                mode="tool_safety",
                allowed=True,
                reason="allowed",
                raw_output="allowed",
                score=0.0,
            )
        )
        tool_called = {"value": False}

        def lookup(**kwargs):
            tool_called["value"] = True
            return "lookup-ok"

        SequencedAgentCore.responses = [
            json.dumps({"tool_calls": [{"function_name": "lookup", "args": {"city": "Beijing"}}]}),
            json.dumps({"function_name": "lookup", "args": {"city": "Beijing"}}),
            "Final Answer: done",
        ]
        agent = SecPlanExecuteAgent(
            system_template="{available_tool_descriptions}\n{available_tool_names}",
            agentic_model=SimpleNamespace(model_type="api"),
            guard_model=guard,
            max_turns=1,
        )

        with patch("agents.sec_planexecute_agent.AgentCore", SequencedAgentCore):
            logs, _, _ = agent.agent_invoke(
                query="look up the city",
                available_tool_descriptions={"lookup": "look things up"},
                available_tool_params={},
                known_actions={"lookup": lookup},
            )

        self.assertTrue(tool_called["value"])
        self.assertEqual(len(guard.tool_requests), 1)
        self.assertIn("lookup-ok", logs)

    def test_react_firewall_blocks_on_alignment_decision(self) -> None:
        guard = FakeGuard(
            alignment_decision=GuardDecision(
                mode="alignment",
                allowed=False,
                reason="misaligned",
                raw_output='{"conclusion": true}',
            )
        )
        tool_called = {"value": False}

        def read_file(**kwargs):
            tool_called["value"] = True
            return "file"

        SequencedAgentCore.responses = [
            '(1) Thought: use tool\n(2) Action: read_file\n(3) Action Input: {"path": "/tmp/x"}'
        ]
        agent = ReActFirewallAgent(
            system_template="{available_tool_descriptions}\n{available_tool_names}",
            agentic_model=SimpleNamespace(model_type="api"),
            guard_model=guard,
            max_turns=1,
        )

        with patch("agents.react_firewall_agent.AgentCore", SequencedAgentCore):
            _, messages, _ = agent.agent_invoke(
                query="read the file",
                available_tool_descriptions={"read_file": "read file"},
                available_tool_params={},
                known_actions={"read_file": read_file},
            )

        self.assertFalse(tool_called["value"])
        self.assertEqual(len(guard.alignment_requests), 1)
        self.assertEqual(messages[-1]["content"], "Sorry, I can't assist with the request")


if __name__ == "__main__":
    unittest.main()
