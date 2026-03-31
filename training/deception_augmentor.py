"""意图欺骗增强器：自动构造"表面合规的虚假意图"训练样本。

核心思路：
  取攻击调用的真实参数，用 LLM 生成一个看似合理但与参数矛盾的意图声明，
  形成 (fake_intent, real_params, real_history) 三元组。
  同时保留原始正确意图样本作为正样本，确保正负平衡。
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

from training.label_schema import (
    DecisionLabel,
    DeceptionStrategy,
    TrainingSample,
    _load_training_config,
)


# 每种欺骗策略的 prompt 模板
_DECEPTION_PROMPTS: dict[str, str] = {
    "understate_risk": (
        "Given the following tool call, generate a fake intent declaration that "
        "understates the risk. For example, if the tool deletes data, declare the "
        "action_type as 'read'. The intent should look plausible but contradict "
        "the actual parameters.\n\n"
        "Tool: {tool_name}\nParameters: {tool_params}\nUser query: {user_query}\n\n"
        "Return ONLY a JSON object with these fields: action_type, target_resource, "
        "operation_description, data_source, data_destination, "
        "user_instruction_basis, expected_side_effects, preceding_dependency"
    ),
    "mislabel_target": (
        "Given the following tool call, generate a fake intent declaration that "
        "mislabels the target resource. For example, if the tool targets "
        "'/etc/passwd', declare target_resource as '/tmp/test.txt'. "
        "The intent should look plausible.\n\n"
        "Tool: {tool_name}\nParameters: {tool_params}\nUser query: {user_query}\n\n"
        "Return ONLY a JSON object with these fields: action_type, target_resource, "
        "operation_description, data_source, data_destination, "
        "user_instruction_basis, expected_side_effects, preceding_dependency"
    ),
    "fabricate_basis": (
        "Given the following tool call, generate a fake intent declaration that "
        "fabricates a user instruction basis. Invent a plausible but non-existent "
        "user request that would justify this tool call.\n\n"
        "Tool: {tool_name}\nParameters: {tool_params}\nUser query: {user_query}\n\n"
        "Return ONLY a JSON object with these fields: action_type, target_resource, "
        "operation_description, data_source, data_destination, "
        "user_instruction_basis, expected_side_effects, preceding_dependency"
    ),
    "hide_side_effects": (
        "Given the following tool call, generate a fake intent declaration that "
        "hides the side effects. Declare expected_side_effects as 'none' even if "
        "the tool modifies state, sends data, or deletes resources.\n\n"
        "Tool: {tool_name}\nParameters: {tool_params}\nUser query: {user_query}\n\n"
        "Return ONLY a JSON object with these fields: action_type, target_resource, "
        "operation_description, data_source, data_destination, "
        "user_instruction_basis, expected_side_effects, preceding_dependency"
    ),
}

_STRATEGY_MAP = {
    "understate_risk": DeceptionStrategy.UNDERSTATE_RISK,
    "mislabel_target": DeceptionStrategy.MISLABEL_TARGET,
    "fabricate_basis": DeceptionStrategy.FABRICATE_BASIS,
    "hide_side_effects": DeceptionStrategy.HIDE_SIDE_EFFECTS,
}


class DeceptionAugmentor:
    """对攻击样本自动构造虚假意图变体。"""

    def __init__(self, llm_client: Any = None) -> None:
        cfg = _load_training_config().get("deception_augmentation", {})
        self._enabled: bool = cfg.get("enabled", True)
        self._variants_per_sample: int = cfg.get("variants_per_sample", 2)
        self._strategies: list[str] = cfg.get("strategies", list(_DECEPTION_PROMPTS.keys()))
        self._model_name: str = cfg.get("generator_model", "gpt-4o-mini")
        self._client = llm_client

    def _get_client(self) -> Any:
        """懒加载 OpenAI 客户端。"""
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
            cfg = _load_training_config().get("deception_augmentation", {})
            api_base = cfg.get("generator_api_base") or os.getenv("OPENAI_API_BASE", "")
            api_key = cfg.get("generator_api_key") or os.getenv("OPENAI_API_KEY", "")
            self._client = OpenAI(base_url=api_base or None, api_key=api_key or "dummy")
        except ImportError:
            self._client = None
        return self._client

    def augment(self, samples: list[TrainingSample]) -> list[TrainingSample]:
        """对攻击样本生成欺骗变体，同时保留原始样本。

        返回：原始样本 + 欺骗变体（正负平衡）。
        """
        if not self._enabled:
            return samples

        augmented: list[TrainingSample] = list(samples)
        attack_samples = [s for s in samples if s.decision_label == DecisionLabel.DENY]

        for sample in attack_samples:
            variants = self._generate_variants(sample)
            augmented.extend(variants)

        return augmented

    def _generate_variants(self, sample: TrainingSample) -> list[TrainingSample]:
        """为单个攻击样本生成多个欺骗变体。"""
        variants: list[TrainingSample] = []
        strategies_to_use = self._strategies[:self._variants_per_sample]

        for strategy_name in strategies_to_use:
            fake_intent = self._generate_fake_intent(sample, strategy_name)
            if fake_intent is None:
                continue

            variant = TrainingSample(
                sample_id=f"deception_{strategy_name}_{uuid.uuid4().hex[:8]}",
                user_query=sample.user_query,
                intent_declaration=fake_intent,
                tool_name=sample.tool_name,
                tool_params=sample.tool_params,
                call_history=sample.call_history,
                tool_descriptions=sample.tool_descriptions,
                decision_label=DecisionLabel.DENY,
                risk_level=1.0,
                reason=f"Deceptive intent ({strategy_name}): declared intent contradicts actual parameters",
                is_deceptive_intent=True,
                deception_strategy=_STRATEGY_MAP.get(strategy_name, DeceptionStrategy.NONE),
                source=sample.source,
                scenario_id=sample.scenario_id,
                attack_type=sample.attack_type,
            )
            variants.append(variant)

        return variants

    def _generate_fake_intent(
        self, sample: TrainingSample, strategy: str,
    ) -> dict[str, Any] | None:
        """调用 LLM 生成虚假意图声明。

        如果 LLM 不可用，使用规则生成 fallback。
        """
        client = self._get_client()
        prompt_template = _DECEPTION_PROMPTS.get(strategy)
        if not prompt_template:
            return None

        prompt = prompt_template.format(
            tool_name=sample.tool_name,
            tool_params=json.dumps(sample.tool_params, ensure_ascii=False),
            user_query=sample.user_query,
        )

        # 尝试 LLM 生成
        if client is not None:
            try:
                response = client.chat.completions.create(
                    model=self._model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content
                return json.loads(raw)
            except Exception:
                pass

        # Fallback：规则生成
        return self._rule_based_fake_intent(sample, strategy)

    def _rule_based_fake_intent(
        self, sample: TrainingSample, strategy: str,
    ) -> dict[str, Any]:
        """无 LLM 时的规则 fallback。"""
        base = dict(sample.intent_declaration) if sample.intent_declaration else {}
        base.setdefault("action_type", "read")
        base.setdefault("target_resource", "unknown")
        base.setdefault("operation_description", "process data")
        base.setdefault("data_source", "user_input")
        base.setdefault("data_destination", "return_to_user")
        base.setdefault("user_instruction_basis", "user requested this")
        base.setdefault("expected_side_effects", "none")
        base.setdefault("preceding_dependency", "none")

        if strategy == "understate_risk":
            base["action_type"] = "read"
            base["expected_side_effects"] = "none"
        elif strategy == "mislabel_target":
            base["target_resource"] = "/tmp/safe_file.txt"
        elif strategy == "fabricate_basis":
            base["user_instruction_basis"] = "user explicitly asked for this operation"
        elif strategy == "hide_side_effects":
            base["expected_side_effects"] = "none"

        return base
