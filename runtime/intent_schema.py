"""结构化意图 Schema 定义。

字段枚举与约束从 configs/intent_schema.yaml 加载，
避免硬编码，方便实验时调整字段定义。

设计原则：
  所有字段都是可被护卫模型交叉验证的事实性声明，
  不包含任何"自我安全评估"类字段。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# 默认配置路径，可通过环境变量覆盖
_DEFAULT_CONFIG = Path(__file__).parent.parent / "configs" / "intent_schema.yaml"
_CONFIG_PATH = Path(os.getenv("INTENT_SCHEMA_CONFIG", str(_DEFAULT_CONFIG)))

_schema_config: dict | None = None


def _load_config() -> dict:
    global _schema_config
    if _schema_config is None:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _schema_config = yaml.safe_load(f)
    return _schema_config


def reload_config() -> dict:
    """强制重新加载配置（测试用）。"""
    global _schema_config
    _schema_config = None
    return _load_config()


def get_allowed_values(field_name: str) -> list[str] | None:
    """返回某字段的合法枚举值，无约束则返回 None。"""
    cfg = _load_config()
    field_def = cfg.get("fields", {}).get(field_name, {})
    return field_def.get("allowed_values")


def get_fallback_config() -> dict:
    return _load_config().get("fallback", {})


@dataclass
class IntentDeclaration:
    """单次工具调用的结构化意图声明。

    每个字段都是可被护卫模型交叉验证的事实性声明：
    - action_type + target_resource + operation_description → 与工具参数交叉验证
    - data_source + data_destination → 追踪数据流，检测异常流向
    - user_instruction_basis → 与用户原始 query 交叉验证，检测越权
    - expected_side_effects → 评估操作不可逆性
    - preceding_dependency → 验证任务链逻辑连贯性
    """

    action_type: str = ""
    target_resource: str = ""
    operation_description: str = ""
    data_source: str = ""
    data_destination: str = ""
    user_instruction_basis: str = ""
    expected_side_effects: str = ""
    preceding_dependency: str = "none"

    # 原始文本，解析失败时保留供调试
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "target_resource": self.target_resource,
            "operation_description": self.operation_description,
            "data_source": self.data_source,
            "data_destination": self.data_destination,
            "user_instruction_basis": self.user_instruction_basis,
            "expected_side_effects": self.expected_side_effects,
            "preceding_dependency": self.preceding_dependency,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntentDeclaration":
        return cls(
            action_type=data.get("action_type", ""),
            target_resource=data.get("target_resource", ""),
            operation_description=data.get("operation_description", ""),
            data_source=data.get("data_source", ""),
            data_destination=data.get("data_destination", ""),
            user_instruction_basis=data.get("user_instruction_basis", ""),
            expected_side_effects=data.get("expected_side_effects", ""),
            preceding_dependency=data.get("preceding_dependency", "none"),
        )

    def validate(self) -> list[str]:
        """基础格式校验，返回错误列表（空列表表示通过）。"""
        errors: list[str] = []
        cfg = _load_config()
        fields_def = cfg.get("fields", {})

        for fname, fdef in fields_def.items():
            val = getattr(self, fname, None)
            if fdef.get("required") and not val:
                errors.append(f"Missing required field: {fname}")
                continue
            allowed = fdef.get("allowed_values")
            if allowed and val:
                if isinstance(val, list):
                    bad = [v for v in val if v not in allowed]
                    if bad:
                        errors.append(f"Field '{fname}' has invalid values: {bad}. Allowed: {allowed}")
                elif val not in allowed:
                    errors.append(f"Field '{fname}' value '{val}' not in allowed: {allowed}")

        return errors

    @property
    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    @classmethod
    def make_fallback(cls, raw_text: str = "") -> "IntentDeclaration":
        """解析失败时构造保守的 fallback 意图。

        所有字段填 unknown，护卫模型看到 unknown 会自动提高审查力度。
        """
        return cls(
            action_type="execute",
            target_resource="unknown",
            operation_description="unknown - intent parsing failed",
            data_source="agent_generated",
            data_destination="external_service",
            user_instruction_basis="unknown",
            expected_side_effects="unknown",
            preceding_dependency="none",
            raw_text=raw_text,
        )
