## Context

`GuardTrainer.prepare_sft_data()` 将每条 `TrainingSample` 转为 SFT messages 格式时，用 `1.0 - risk_level` 统一公式为四个交叉验证维度生成分数。唯一的差异是 `intent_vs_history` 做了 `* 0.5` 衰减。这导致训练数据中四个维度高度相关，模型无法学到维度特异性的判断能力。

现有数据结构中 `TrainingSample` 已包含 `attack_type`（NONE/OPI/DPI/HARMFUL/INJECTION）和 `deception_strategy`（4 种欺骗策略），这些信息足以驱动差异化标注，无需修改上游流水线。

## Goals / Non-Goals

**Goals:**
- 不同攻击类型的 SFT 标签在四个维度上呈现不同的分数分布
- OPI 攻击重点体现在 `intent_vs_params` 和 `intent_vs_history` 低分
- DPI 攻击重点体现在 `intent_vs_user_query` 低分
- 意图欺骗样本重点体现在 `intent_vs_params` 低分
- `contradictions` 字段包含维度特异性的矛盾描述
- 维度映射配置可在 `training_config.yaml` 中调整

**Non-Goals:**
- 不修改 `DataCollector`、`TraceGenerator`、`SampleConstructor`、`DeceptionAugmentor`
- 不修改 `samples.jsonl` 格式（只影响 `sft_data.jsonl` 的生成）
- 不引入新的外部依赖
- 不改变 SFT messages 的整体结构（system/user/assistant 三段式不变）

## Decisions

1. **配置驱动 vs 硬编码映射**
   - 选择：在 `training_config.yaml` 中新增 `dimension_profiles` 配置段
   - 理由：与项目"配置外置"的一贯风格一致，方便实验调参
   - 替代方案：硬编码在 `train_guard.py` 中 — 否决，不利于消融实验

2. **线性系数映射 vs 查找表**
   - 选择：每个 (attack_type, dimension) 对应一个系数 `w`，分数 = `1.0 - risk_level * w`
   - 理由：简单、可解释、易配置。`w=1.0` 表示该维度完全反映风险，`w=0.2` 表示该维度几乎不受影响
   - 替代方案：为每个组合定义完整的分数查找表 — 过于复杂，且 risk_level 是连续值

3. **contradictions 生成方式**
   - 选择：为每个 (attack_type, dimension) 预定义矛盾描述模板，仅在该维度分数低于阈值时填充
   - 理由：比统一复制 `reason` 更有信息量，比 LLM 生成更可控
   - 阈值：分数 < 0.5 时填充 contradictions

4. **默认 profile 处理**
   - 选择：未配置的 attack_type 回退到 `default` profile（全维度 `w=1.0`，即现有行为）
   - 理由：向后兼容，新增攻击类型时不会 break

## Risks / Trade-offs

- **系数选择的主观性** → 初始值基于攻击语义分析，后续可通过消融实验调优
- **过拟合到攻击类型** → `default` profile 保底，ALLOW 样本全维度高分不受影响
- **已有 sft_data.jsonl 失效** → 需要重新运行 `prepare_sft_data()`，但 `samples.jsonl` 不受影响
