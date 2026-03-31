"""细粒度决策器：综合交叉验证分数与策略规则产出最终决策。"""

from __future__ import annotations

from guardrail import (
    CrossValidationResult,
    DecisionType,
    GuardrailDecision,
    ModifySubtype,
    PolicyMatch,
    get_thresholds,
)


class DecisionMaker:
    """从 configs/decision_types.yaml 加载阈值，映射分数+规则→决策。"""

    def __init__(self) -> None:
        th = get_thresholds()
        self._allow_min: float = float(th.get("allow_min_score", 0.8))
        self._deny_max: float = float(th.get("deny_max_score", 0.3))
        self._confirm_range: list[float] = [float(v) for v in th.get("confirm_range", [0.3, 0.5])]
        self._modify_range: list[float] = [float(v) for v in th.get("modify_range", [0.5, 0.8])]

    def decide(
        self,
        cross_result: CrossValidationResult,
        policy_matches: list[PolicyMatch],
    ) -> GuardrailDecision:
        # 1. 策略硬覆盖（按 priority 从高到低，第一个生效）
        for pm in policy_matches:
            if pm.effect == "deny":
                return GuardrailDecision(
                    decision_type=DecisionType.DENY,
                    reason=f"Policy rule '{pm.rule_name}' triggered deny",
                    confidence=1.0,
                )
            if pm.effect == "require_confirm":
                return GuardrailDecision(
                    decision_type=DecisionType.CONFIRM,
                    reason=f"Policy rule '{pm.rule_name}' requires confirmation",
                    confidence=0.8,
                )
            if pm.effect == "allow":
                return GuardrailDecision(
                    decision_type=DecisionType.ALLOW,
                    reason=f"Policy rule '{pm.rule_name}' allows this action",
                    confidence=1.0,
                )

        # 2. 按 holistic_score 映射
        score = cross_result.holistic_score

        if score >= self._allow_min:
            return GuardrailDecision(
                decision_type=DecisionType.ALLOW,
                reason=f"Cross-validation holistic score {score:.2f} >= {self._allow_min}",
                confidence=score,
            )

        if score <= self._deny_max:
            contradictions = cross_result.holistic.contradictions
            return GuardrailDecision(
                decision_type=DecisionType.DENY,
                reason=f"Cross-validation holistic score {score:.2f} <= {self._deny_max}. "
                       f"Contradictions: {contradictions}",
                confidence=1.0 - score,
            )

        if self._confirm_range[0] < score <= self._confirm_range[1]:
            return GuardrailDecision(
                decision_type=DecisionType.CONFIRM,
                reason=f"Cross-validation holistic score {score:.2f} in confirm range",
                confidence=score,
            )

        # modify range: score between confirm_range[1] and allow_min
        return GuardrailDecision(
            decision_type=DecisionType.MODIFY,
            reason=f"Cross-validation holistic score {score:.2f} in modify range",
            confidence=score,
            modify_subtype=ModifySubtype.DOWNSCOPE,
        )
