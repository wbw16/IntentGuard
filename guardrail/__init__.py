"""guardrail — 意图感知护栏中间件。

提供多维交叉验证、策略规则引擎、细粒度决策和审计日志。
"""

from __future__ import annotations

import enum
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from runtime.intent_schema import IntentDeclaration

# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

_DEFAULT_DECISION_CONFIG = Path(__file__).parent.parent / "configs" / "decision_types.yaml"
_DECISION_CONFIG_PATH = Path(
    os.getenv("DECISION_TYPES_CONFIG", str(_DEFAULT_DECISION_CONFIG))
)

_decision_config: dict | None = None


def _load_decision_config() -> dict:
    global _decision_config
    if _decision_config is None:
        with open(_DECISION_CONFIG_PATH, "r", encoding="utf-8") as f:
            _decision_config = yaml.safe_load(f)
    return _decision_config


def reload_decision_config() -> dict:
    """强制重新加载（测试用）。"""
    global _decision_config
    _decision_config = None
    return _load_decision_config()


def get_thresholds() -> dict:
    return _load_decision_config().get("thresholds", {})


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------


class DecisionType(enum.Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    MODIFY = "MODIFY"
    CONFIRM = "CONFIRM"


class ModifySubtype(enum.Enum):
    DOWNSCOPE = "downscope"
    REWRITE = "rewrite"
    SANITIZE = "sanitize"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class DimensionScore:
    """单个交叉验证维度的评分结果。"""

    score: float = 0.0
    contradictions: list[str] = field(default_factory=list)
    evidence: str = ""


@dataclass
class CrossValidationResult:
    """四维交叉验证的完整结果。"""

    intent_vs_params: DimensionScore = field(default_factory=DimensionScore)
    intent_vs_user_query: DimensionScore = field(default_factory=DimensionScore)
    intent_vs_history: DimensionScore = field(default_factory=DimensionScore)
    holistic: DimensionScore = field(default_factory=DimensionScore)
    degraded: bool = False

    @property
    def holistic_score(self) -> float:
        return self.holistic.score

    def to_dict(self) -> dict[str, Any]:
        def _dim(d: DimensionScore) -> dict:
            return {"score": d.score, "contradictions": d.contradictions, "evidence": d.evidence}
        return {
            "intent_vs_params": _dim(self.intent_vs_params),
            "intent_vs_user_query": _dim(self.intent_vs_user_query),
            "intent_vs_history": _dim(self.intent_vs_history),
            "holistic": _dim(self.holistic),
            "degraded": self.degraded,
        }


@dataclass
class PolicyMatch:
    """策略规则命中记录。"""

    rule_name: str = ""
    effect: str = ""       # allow | deny | require_confirm
    priority: int = 0


@dataclass
class GuardrailDecision:
    """护栏中间件的最终决策。"""

    decision_type: DecisionType = DecisionType.ALLOW
    reason: str = ""
    confidence: float = 1.0
    modified_params: dict[str, Any] | None = None
    modify_subtype: ModifySubtype | None = None
    cross_validation: CrossValidationResult | None = None
    policy_matches: list[PolicyMatch] = field(default_factory=list)
    audit_record: dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.decision_type == DecisionType.ALLOW

    @property
    def blocked(self) -> bool:
        return self.decision_type == DecisionType.DENY

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "decision_type": self.decision_type.value,
            "reason": self.reason,
            "confidence": self.confidence,
        }
        if self.modified_params is not None:
            result["modified_params"] = self.modified_params
        if self.modify_subtype is not None:
            result["modify_subtype"] = self.modify_subtype.value
        if self.cross_validation is not None:
            result["cross_validation"] = self.cross_validation.to_dict()
        if self.policy_matches:
            result["policy_matches"] = [
                {"rule_name": m.rule_name, "effect": m.effect, "priority": m.priority}
                for m in self.policy_matches
            ]
        return result


# ---------------------------------------------------------------------------
# GuardrailMiddleware — 组合入口
# ---------------------------------------------------------------------------


class GuardrailMiddleware:
    """护栏中间件：组合交叉验证、策略引擎、决策器和审计日志。"""

    def __init__(self, guard_model: Any, *, audit_dir: str | None = None, audit_enabled: bool = True):
        from .cross_validator import CrossValidator
        from .policy_engine import PolicyEngine
        from .decision_maker import DecisionMaker
        from .audit_logger import AuditLogger

        self.cross_validator = CrossValidator(guard_model)
        self.policy_engine = PolicyEngine()
        self.decision_maker = DecisionMaker()
        self.audit_logger = AuditLogger(output_dir=audit_dir, enabled=audit_enabled)

    def evaluate(
        self,
        intent: "IntentDeclaration",
        tool_name: str,
        tool_params: dict,
        query: str,
        history: list,
        tool_descriptions: str = "",
    ) -> GuardrailDecision:
        cross_result = self.cross_validator.validate(
            intent, tool_name, tool_params, query, history, tool_descriptions,
        )
        policy_matches = self.policy_engine.evaluate(intent)
        decision = self.decision_maker.decide(cross_result, policy_matches)
        decision.cross_validation = cross_result
        decision.policy_matches = policy_matches
        decision.audit_record = self.audit_logger.log(
            intent=intent,
            tool_name=tool_name,
            tool_params=tool_params,
            query=query,
            cross_result=cross_result,
            policy_matches=policy_matches,
            decision=decision,
        )
        return decision
