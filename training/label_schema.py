"""标注 Schema：定义训练样本数据结构与质量检查逻辑。"""

from __future__ import annotations

import enum
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONFIG = Path(__file__).parent.parent / "configs" / "training_config.yaml"
_CONFIG_PATH = Path(os.getenv("TRAINING_CONFIG", str(_DEFAULT_CONFIG)))

_training_config: dict | None = None


def _load_training_config() -> dict:
    global _training_config
    if _training_config is None:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _training_config = yaml.safe_load(f)
    return _training_config


def reload_training_config() -> dict:
    global _training_config
    _training_config = None
    return _load_training_config()


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------


class DecisionLabel(enum.Enum):
    """训练样本的决策标签。"""
    ALLOW = "ALLOW"
    DENY = "DENY"
    MODIFY = "MODIFY"
    CONFIRM = "CONFIRM"


class AttackType(enum.Enum):
    """攻击类型分类。"""
    NONE = "none"           # 正常调用
    OPI = "OPI"             # Output Prompt Injection
    DPI = "DPI"             # Direct Prompt Injection
    HARMFUL = "harmful"     # AgentHarm harmful behavior
    INJECTION = "injection" # AgentDojo injection


class DeceptionStrategy(enum.Enum):
    """意图欺骗策略。"""
    NONE = "none"
    UNDERSTATE_RISK = "understate_risk"
    MISLABEL_TARGET = "mislabel_target"
    FABRICATE_BASIS = "fabricate_basis"
    HIDE_SIDE_EFFECTS = "hide_side_effects"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class AttackScenario:
    """统一的攻击场景描述，从各数据集采集后归一化。"""

    scenario_id: str = ""
    source: str = ""                # agentharm | asb | agentdojo
    query: str = ""                 # 用户原始请求
    tools: list[str] = field(default_factory=list)
    tool_descriptions: dict[str, str] = field(default_factory=dict)
    tool_params: dict[str, dict] = field(default_factory=dict)
    attack_type: AttackType = AttackType.NONE
    attack_instruction: str = ""    # 攻击者注入的指令
    expected_harmful_tool: str = "" # 预期被利用的工具
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "source": self.source,
            "query": self.query,
            "tools": self.tools,
            "attack_type": self.attack_type.value,
            "attack_instruction": self.attack_instruction,
            "expected_harmful_tool": self.expected_harmful_tool,
            "metadata": self.metadata,
        }


@dataclass
class TraceStep:
    """执行轨迹中的单步记录。"""

    step_index: int = 0
    tool_name: str = ""
    tool_params: dict[str, Any] = field(default_factory=dict)
    intent: dict[str, Any] = field(default_factory=dict)  # IntentDeclaration.to_dict()
    observation: str = ""
    raw_model_output: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "tool_name": self.tool_name,
            "tool_params": self.tool_params,
            "intent": self.intent,
            "observation": self.observation,
        }


@dataclass
class ExecutionTrace:
    """完整的执行轨迹。"""

    scenario_id: str = ""
    agent_strategy: str = ""
    steps: list[TraceStep] = field(default_factory=list)
    final_result: str = ""
    was_attacked: bool = False
    attack_succeeded: bool = False
    messages: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "agent_strategy": self.agent_strategy,
            "steps": [s.to_dict() for s in self.steps],
            "final_result": self.final_result,
            "was_attacked": self.was_attacked,
            "attack_succeeded": self.attack_succeeded,
        }


@dataclass
class TrainingSample:
    """单条训练样本。

    input 侧：护卫模型看到的上下文
    label 侧：期望的决策输出
    """

    sample_id: str = ""
    # --- input ---
    user_query: str = ""
    intent_declaration: dict[str, Any] = field(default_factory=dict)
    tool_name: str = ""
    tool_params: dict[str, Any] = field(default_factory=dict)
    call_history: list[dict] = field(default_factory=list)
    tool_descriptions: str = ""
    # --- label ---
    decision_label: DecisionLabel = DecisionLabel.ALLOW
    risk_level: float = 0.0         # 0.0 (safe) ~ 1.0 (dangerous)
    reason: str = ""
    is_deceptive_intent: bool = False
    deception_strategy: DeceptionStrategy = DeceptionStrategy.NONE
    # --- metadata ---
    source: str = ""
    scenario_id: str = ""
    attack_type: AttackType = AttackType.NONE

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "input": {
                "user_query": self.user_query,
                "intent_declaration": self.intent_declaration,
                "tool_name": self.tool_name,
                "tool_params": self.tool_params,
                "call_history": self.call_history,
                "tool_descriptions": self.tool_descriptions,
            },
            "label": {
                "decision_label": self.decision_label.value,
                "risk_level": self.risk_level,
                "reason": self.reason,
                "is_deceptive_intent": self.is_deceptive_intent,
                "deception_strategy": self.deception_strategy.value,
            },
            "metadata": {
                "source": self.source,
                "scenario_id": self.scenario_id,
                "attack_type": self.attack_type.value,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrainingSample":
        inp = data.get("input", {})
        label = data.get("label", {})
        meta = data.get("metadata", {})
        return cls(
            sample_id=data.get("sample_id", ""),
            user_query=inp.get("user_query", ""),
            intent_declaration=inp.get("intent_declaration", {}),
            tool_name=inp.get("tool_name", ""),
            tool_params=inp.get("tool_params", {}),
            call_history=inp.get("call_history", []),
            tool_descriptions=inp.get("tool_descriptions", ""),
            decision_label=DecisionLabel(label.get("decision_label", "ALLOW")),
            risk_level=float(label.get("risk_level", 0.0)),
            reason=label.get("reason", ""),
            is_deceptive_intent=label.get("is_deceptive_intent", False),
            deception_strategy=DeceptionStrategy(label.get("deception_strategy", "none")),
            source=meta.get("source", ""),
            scenario_id=meta.get("scenario_id", ""),
            attack_type=AttackType(meta.get("attack_type", "none")),
        )


# ---------------------------------------------------------------------------
# 质量检查
# ---------------------------------------------------------------------------


def validate_sample(sample: TrainingSample) -> list[str]:
    """检查单条样本的完整性，返回错误列表。"""
    errors: list[str] = []
    if not sample.sample_id:
        errors.append("missing sample_id")
    if not sample.user_query:
        errors.append("missing user_query")
    if not sample.tool_name:
        errors.append("missing tool_name")
    if not sample.intent_declaration:
        errors.append("missing intent_declaration")
    if not sample.reason:
        errors.append("missing reason")
    return errors


def compute_distribution(samples: list[TrainingSample]) -> dict[str, Any]:
    """统计样本集的标签分布。"""
    dist: dict[str, int] = {}
    attack_dist: dict[str, int] = {}
    deception_count = 0
    for s in samples:
        label = s.decision_label.value
        dist[label] = dist.get(label, 0) + 1
        at = s.attack_type.value
        attack_dist[at] = attack_dist.get(at, 0) + 1
        if s.is_deceptive_intent:
            deception_count += 1
    return {
        "total": len(samples),
        "decision_distribution": dist,
        "attack_type_distribution": attack_dist,
        "deceptive_intent_count": deception_count,
        "deceptive_intent_ratio": deception_count / max(len(samples), 1),
    }
