## Why

当前 `GuardTrainer.prepare_sft_data()` 用 `1.0 - risk_level` 统一公式生成四个交叉验证维度的分数，导致 `intent_vs_params`、`intent_vs_user_query`、`intent_vs_history`、`holistic` 几乎相同。训练出的护卫模型无法学到"不同攻击类型的矛盾出现在不同维度"这一关键模式，交叉验证退化为单维度判断。

## What Changes

- 新增攻击类型→维度矛盾映射配置（`configs/training_config.yaml` 中扩展）
- 重写 `train_guard.py` 中 `prepare_sft_data()` 的分数生成逻辑，根据 `attack_type` 和 `deception_strategy` 为四个维度生成差异化分数
- 为 `contradictions` 字段生成维度特异性的矛盾描述，而非统一复制 `reason`
- 不改变数据采集、轨迹生成、样本构造流程，仅影响 SFT 数据的标签质量

## Capabilities

### New Capabilities

- `dimension-aware-labeling`: 基于攻击类型和欺骗策略的差异化四维分数生成，使训练数据中每个维度的分数反映该维度实际应检测到的矛盾程度

### Modified Capabilities

（无已有 spec 需要修改）

## Impact

- `training/train_guard.py`: `prepare_sft_data()` 方法重写分数生成逻辑
- `configs/training_config.yaml`: 新增 `dimension_profiles` 配置段
- `tests/test_training.py`: `test_prepare_sft_data` 测试用例需更新以验证差异化分数
- 已生成的 `sft_data.jsonl` 需要重新生成（不影响 `samples.jsonl`）
