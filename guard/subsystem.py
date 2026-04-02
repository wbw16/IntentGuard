from __future__ import annotations

"""Public Guard subsystem interface and decision normalization."""

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from runtime.guardian_parser import alignment_check_parser, guardian_parser_map
from runtime.prompts import GUARD_TEMPLATES

if TYPE_CHECKING:
    from .config import GuardConfig
    from runtime.modeling import StandaloneModel


DEFAULT_GUARD_TEMPLATE_KEY = "qwen2.5-7b-instruct"
DEFAULT_GUARD_MAX_ATTEMPTS = 3
DEFAULT_GUARD_BLOCK_THRESHOLD = 0.5


@dataclass(frozen=True)
class GuardEvaluationRequest:
    """Normalized guard input shared by callers."""

    user_request: str
    interaction_history: Any
    current_action: Any
    current_action_description: str

    @classmethod
    def from_legacy_meta_info(cls, meta_info: dict[str, Any]) -> "GuardEvaluationRequest":
        agent_action = meta_info.get("agent_action", {})
        return cls(
            user_request=meta_info.get("user_request", ""),
            interaction_history=meta_info.get("interaction_history", agent_action.get("interaction_history", [])),
            current_action=meta_info.get("current_action", agent_action.get("current_action")),
            current_action_description=meta_info.get("current_action_description", meta_info.get("env_info", "")),
        )

    def to_template_context(self) -> dict[str, Any]:
        return {
            "env_info": self.current_action_description,
            "user_request": self.user_request,
            "agent_action": {
                "interaction_history": self.interaction_history,
                "current_action": self.current_action,
            },
        }


@dataclass(frozen=True)
class GuardDecision:
    """Normalized Guard decision consumed by agents."""

    mode: str
    allowed: bool
    reason: str
    raw_output: str
    degraded: bool = False
    score: float | None = None
    normalized_details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    template_key: str | None = None
    parser_key: str | None = None

    @property
    def blocked(self) -> bool:
        return not self.allowed

    def to_tool_result(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "mode": self.mode,
            "allowed": self.allowed,
            "degraded": self.degraded,
            "reason": self.reason,
            "raw_output": self.raw_output,
        }
        if self.error is not None:
            payload["error"] = self.error
        if self.template_key is not None:
            payload["template_key"] = self.template_key
        if self.parser_key is not None:
            payload["parser_key"] = self.parser_key
        if self.mode == "tool_safety":
            if self.score is not None:
                payload["risk rating"] = self.score
            payload["results"] = dict(self.normalized_details)
        else:
            payload["alignment_check_passed"] = self.allowed
            if self.normalized_details:
                payload["results"] = dict(self.normalized_details)
        return payload


class GuardSubsystem:
    """First-class Guard interface that owns evaluation and normalization."""

    def __init__(self, config: "GuardConfig", model: "StandaloneModel" | None = None):
        from runtime.modeling import StandaloneModel

        self.config = config
        self._model = model or StandaloneModel(config.model_config)

    @property
    def client(self):
        return self._model.client

    @property
    def model_name(self) -> str:
        return self._model.model_name

    @property
    def model_type(self) -> str:
        return self._model.model_type

    @property
    def sampling(self):
        return self._model.sampling

    @property
    def temperature(self) -> float:
        return self._model.temperature

    def _resolve_template_key(self) -> str:
        if self.model_name in GUARD_TEMPLATES:
            return self.model_name
        return self.config.default_template_key

    def _resolve_parser_key(self) -> str:
        if self.model_name in guardian_parser_map:
            return self.model_name
        return self.config.default_template_key

    def _invoke_model(self, messages: list[dict[str, Any]], *, json_format: bool = False) -> str:
        if self.model_type == "api":
            request: dict[str, Any] = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
            }
            if json_format:
                request["response_format"] = {"type": "json_object"}
            response = self.client.chat.completions.create(**request)
            return response.choices[0].message.content

        response = self.client.chat(messages, sampling_params=self.sampling)
        return response[0].outputs[0].text.strip()

    def _normalize_tool_safety_decision(
        self,
        *,
        parser_result: float | None,
        raw_output: str,
        results: dict[str, Any],
        degraded: bool,
        error: str | None,
        template_key: str,
        parser_key: str,
    ) -> GuardDecision:
        if parser_result is not None:
            return GuardDecision(
                mode="tool_safety",
                allowed=parser_result < self.config.block_threshold,
                reason=raw_output,
                raw_output=raw_output,
                score=parser_result,
                normalized_details=dict(results),
                degraded=degraded,
                error=error,
                template_key=template_key,
                parser_key=parser_key,
            )

        return GuardDecision(
            mode="tool_safety",
            allowed=error is None,
            reason=raw_output or (error or "guard evaluation degraded"),
            raw_output=raw_output,
            normalized_details=dict(results),
            degraded=True,
            error=error or "unparsed_guard_output",
            template_key=template_key,
            parser_key=parser_key,
        )

    def _normalize_alignment_decision(
        self,
        *,
        parser_result: bool | None,
        raw_output: str,
        degraded: bool,
        error: str | None,
    ) -> GuardDecision:
        if parser_result is not None:
            return GuardDecision(
                mode="alignment",
                allowed=not parser_result,
                reason=raw_output,
                raw_output=raw_output,
                degraded=degraded,
                normalized_details={"conclusion": parser_result},
                error=error,
                template_key="alignmentcheck",
                parser_key="alignment_check_parser",
            )

        return GuardDecision(
            mode="alignment",
            allowed=error is None,
            reason=raw_output or (error or "alignment evaluation degraded"),
            raw_output=raw_output,
            degraded=True,
            normalized_details={},
            error=error or "unparsed_alignment_output",
            template_key="alignmentcheck",
            parser_key="alignment_check_parser",
        )

    def get_judgment_res(self, meta_info: dict[str, Any], max_turn: int | None = None) -> dict[str, Any]:
        decision = self.review_tool_action(
            GuardEvaluationRequest.from_legacy_meta_info(meta_info),
            max_attempts=max_turn,
        )
        return decision.to_tool_result()

    def review_tool_action(
        self,
        request: GuardEvaluationRequest | dict[str, Any],
        *,
        max_attempts: int | None = None,
    ) -> GuardDecision:
        normalized_request = (
            request
            if isinstance(request, GuardEvaluationRequest)
            else GuardEvaluationRequest.from_legacy_meta_info(request)
        )
        template_key = self._resolve_template_key()
        parser_key = self._resolve_parser_key()
        guard_input = GUARD_TEMPLATES[template_key].format(**normalized_request.to_template_context())
        guard_messages = [{"role": "user", "content": guard_input}]
        attempts = max_attempts or self.config.max_attempts
        raw_output = ""
        last_error: str | None = None
        results: dict[str, Any] = {}

        for _ in range(attempts):
            try:
                raw_output = self._invoke_model(guard_messages)
            except Exception as exc:  # pragma: no cover - external API edge case
                last_error = str(exc)
                continue

            parser = guardian_parser_map.get(parser_key)
            parsed_value = None
            parsed = parser(raw_output) if parser is not None else None
            if isinstance(parsed, tuple):
                parsed_value, results = parsed
            else:
                parsed_value = parsed

            if parsed_value in {0, 0.5, 1, 0.0, 1.0}:
                return self._normalize_tool_safety_decision(
                    parser_result=float(parsed_value),
                    raw_output=raw_output,
                    results=results,
                    degraded=False,
                    error=None,
                    template_key=template_key,
                    parser_key=parser_key,
                )

        return self._normalize_tool_safety_decision(
            parser_result=None,
            raw_output=raw_output,
            results=results,
            degraded=True,
            error=last_error,
            template_key=template_key,
            parser_key=parser_key,
        )

    def review_alignment(
        self,
        request: GuardEvaluationRequest | dict[str, Any],
        *,
        max_attempts: int | None = None,
    ) -> GuardDecision:
        normalized_request = (
            request
            if isinstance(request, GuardEvaluationRequest)
            else GuardEvaluationRequest.from_legacy_meta_info(request)
        )
        system_prompt, user_prompt = GUARD_TEMPLATES["alignmentcheck"]
        guard_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt.format(**normalized_request.to_template_context())},
        ]
        attempts = max_attempts or self.config.max_attempts
        raw_output = ""
        last_error: str | None = None

        for _ in range(attempts):
            try:
                raw_output = self._invoke_model(guard_messages, json_format=self.model_type == "api")
                parser_result = alignment_check_parser(raw_output)
                if parser_result in {True, False}:
                    return self._normalize_alignment_decision(
                        parser_result=parser_result,
                        raw_output=raw_output,
                        degraded=False,
                        error=None,
                    )
            except Exception as exc:  # pragma: no cover - external API edge case
                last_error = str(exc)

        return self._normalize_alignment_decision(
            parser_result=None,
            raw_output=raw_output,
            degraded=True,
            error=last_error,
        )

    def tool_safety_guardian(
        self,
        user_request: str,
        interaction_history: Any,
        current_action: Any,
        current_action_description: str,
    ) -> dict[str, Any]:
        return self.review_tool_action(
            GuardEvaluationRequest(
                user_request=user_request,
                interaction_history=interaction_history,
                current_action=current_action,
                current_action_description=current_action_description,
            )
        ).to_tool_result()

    def alignment_check(
        self,
        user_request: str,
        interaction_history: Any,
        current_action: Any,
        current_action_description: str,
    ) -> dict[str, Any]:
        return self.review_alignment(
            GuardEvaluationRequest(
                user_request=user_request,
                interaction_history=interaction_history,
                current_action=current_action,
                current_action_description=current_action_description,
            )
        ).to_tool_result()

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "tool_safety_guardian":
            return self.tool_safety_guardian(**arguments)
        if tool_name == "alignment_check":
            return self.alignment_check(**arguments)
        return {"reason": "tool name error, expected tool_safety_guardian or alignment_check"}
