"""样本构造器：从执行轨迹中抽取训练样本。

每个轨迹的每一步都可以成为一条独立的训练样本：
- 正常调用 → ALLOW
- 攻击成功的调用 → DENY
- 边界情况 → CONFIRM
"""

from __future__ import annotations

import uuid
from typing import Any

from training.label_schema import (
    AttackScenario,
    AttackType,
    DecisionLabel,
    ExecutionTrace,
    TraceStep,
    TrainingSample,
    _load_training_config,
)


class SampleConstructor:
    """从 ExecutionTrace 中抽取每一步为独立训练样本。"""

    def __init__(self) -> None:
        cfg = _load_training_config().get("sample_construction", {})
        self._label_mapping = cfg.get("label_mapping", {})

    def construct_from_trace(
        self,
        trace: ExecutionTrace,
        scenario: AttackScenario,
    ) -> list[TrainingSample]:
        """从单条轨迹构造训练样本。"""
        samples: list[TrainingSample] = []

        for i, step in enumerate(trace.steps):
            # 构造历史：当前步之前的所有步骤
            call_history = [s.to_dict() for s in trace.steps[:i]]

            # 判断标签
            label, risk, reason = self._determine_label(
                step, trace, scenario,
            )

            samples.append(TrainingSample(
                sample_id=f"{trace.scenario_id}_{trace.agent_strategy}_{i}_{uuid.uuid4().hex[:8]}",
                user_query=scenario.query,
                intent_declaration=step.intent,
                tool_name=step.tool_name,
                tool_params=step.tool_params,
                call_history=call_history,
                tool_descriptions=_format_tool_descriptions(scenario.tool_descriptions),
                decision_label=label,
                risk_level=risk,
                reason=reason,
                is_deceptive_intent=False,
                source=scenario.source,
                scenario_id=scenario.scenario_id,
                attack_type=scenario.attack_type,
            ))

        return samples

    def construct_batch(
        self,
        traces: list[ExecutionTrace],
        scenarios: dict[str, AttackScenario],
    ) -> list[TrainingSample]:
        """批量构造样本。scenarios 按 scenario_id 索引。"""
        all_samples: list[TrainingSample] = []
        for trace in traces:
            scenario = scenarios.get(trace.scenario_id)
            if scenario is None:
                continue
            all_samples.extend(self.construct_from_trace(trace, scenario))
        return all_samples

    def _determine_label(
        self,
        step: TraceStep,
        trace: ExecutionTrace,
        scenario: AttackScenario,
    ) -> tuple[DecisionLabel, float, str]:
        """根据场景和轨迹判断单步的标签。"""
        # 正常场景
        if scenario.attack_type == AttackType.NONE:
            return DecisionLabel.ALLOW, 0.0, "Normal call in benign scenario"

        # 攻击场景中，调用了 harmful tool
        if step.tool_name == scenario.expected_harmful_tool:
            if trace.attack_succeeded:
                return (
                    DecisionLabel.DENY, 1.0,
                    f"Attack succeeded: {step.tool_name} is the harmful tool",
                )
            return (
                DecisionLabel.DENY, 0.8,
                f"Attempted harmful tool call: {step.tool_name}",
            )

        # 攻击场景中的正常工具调用
        if trace.was_attacked and not trace.attack_succeeded:
            return (
                DecisionLabel.ALLOW, 0.2,
                "Normal tool call in attack scenario (attack was blocked)",
            )

        # 攻击场景中的正常工具但攻击最终成功了
        if trace.was_attacked and trace.attack_succeeded:
            return (
                DecisionLabel.CONFIRM, 0.5,
                "Normal tool in scenario where attack eventually succeeded",
            )

        return DecisionLabel.ALLOW, 0.1, "Default: allow"


def _format_tool_descriptions(descs: dict[str, str]) -> str:
    if not descs:
        return ""
    return "\n".join(f"{name}: {desc}" for name, desc in descs.items())
