"""四维交叉验证引擎。

复用已有的 GuardSubsystem 实例做模型调用，
单次 prompt 完成 4 维评分以减少延迟。
"""

from __future__ import annotations

from typing import Any

from guardrail import CrossValidationResult
from guardrail.guard_model_adapter import (
    build_cross_validation_prompt,
    parse_cross_validation_response,
)


class CrossValidator:
    """构造交叉验证 prompt，调用护卫模型，解析 4 维分数。"""

    def __init__(self, guard_model: Any):
        self._guard_model = guard_model

    def validate(
        self,
        intent: Any,
        tool_name: str,
        tool_params: dict,
        query: str,
        history: list,
        tool_descriptions: str = "",
    ) -> CrossValidationResult:
        messages = build_cross_validation_prompt(
            intent, tool_name, tool_params, query, history, tool_descriptions,
        )
        try:
            use_json = getattr(self._guard_model, "model_type", "") == "api"
            raw = self._guard_model._invoke_model(messages, json_format=use_json)
        except Exception:
            return CrossValidationResult(degraded=True)

        return parse_cross_validation_response(raw)
