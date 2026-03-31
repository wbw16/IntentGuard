"""策略规则引擎：从 configs/policy_rules.yaml 加载规则并匹配意图。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from guardrail import PolicyMatch

_DEFAULT_POLICY_CONFIG = Path(__file__).parent.parent / "configs" / "policy_rules.yaml"
_POLICY_CONFIG_PATH = Path(os.getenv("POLICY_RULES_CONFIG", str(_DEFAULT_POLICY_CONFIG)))

_policy_config: dict | None = None


def _load_policy_config() -> dict:
    global _policy_config
    if _policy_config is None:
        with open(_POLICY_CONFIG_PATH, "r", encoding="utf-8") as f:
            _policy_config = yaml.safe_load(f)
    return _policy_config


def reload_policy_config() -> dict:
    global _policy_config
    _policy_config = None
    return _load_policy_config()


class PolicyEngine:
    """根据 YAML 规则匹配意图字段，返回命中的策略列表。"""

    def __init__(self) -> None:
        cfg = _load_policy_config()
        self._rules: list[dict] = cfg.get("rules", [])
        self._fallback_effect: str = cfg.get("fallback_effect", "confirm")

    def _match_rule(self, rule: dict, intent: Any) -> bool:
        """检查单条规则的所有 match 条件是否全部命中。"""
        match_spec = rule.get("match", {})
        for field_name, expected in match_spec.items():
            # 支持 _contains 后缀做子串匹配
            if field_name.endswith("_contains"):
                actual_field = field_name[: -len("_contains")]
                actual_val = str(getattr(intent, actual_field, ""))
                if expected not in actual_val:
                    return False
                continue

            actual_val = getattr(intent, field_name, None)
            if actual_val is None:
                return False

            if isinstance(expected, list):
                if actual_val not in expected:
                    return False
            else:
                if actual_val != expected:
                    return False
        return True

    def evaluate(self, intent: Any) -> list[PolicyMatch]:
        """返回所有命中的规则，按 priority 从高到低排序。"""
        matches: list[PolicyMatch] = []
        for rule in self._rules:
            if self._match_rule(rule, intent):
                matches.append(PolicyMatch(
                    rule_name=rule.get("name", ""),
                    effect=rule.get("effect", ""),
                    priority=rule.get("priority", 0),
                ))
        matches.sort(key=lambda m: m.priority, reverse=True)
        return matches

    @property
    def fallback_effect(self) -> str:
        return self._fallback_effect
