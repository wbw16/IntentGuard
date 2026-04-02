## 1. 配置

- [x] 1.1 在 `configs/training_config.yaml` 中新增 `dimension_profiles` 配置段，包含 OPI、DPI、harmful、injection、deception、default 六个 profile，每个定义四维权重

## 2. 核心实现

- [x] 2.1 在 `training/train_guard.py` 中新增 `_load_dimension_profiles()` 函数，从 training_config.yaml 加载维度映射配置
- [x] 2.2 在 `training/train_guard.py` 中新增 `_compute_dimension_scores(sample, profiles)` 函数，根据 attack_type 和 is_deceptive_intent 选择 profile 并计算四维分数
- [x] 2.3 在 `training/train_guard.py` 中新增 `_generate_contradictions(dimension, score, attack_type, reason)` 函数，为低分维度生成特异性矛盾描述
- [x] 2.4 重写 `prepare_sft_data()` 中 assistant_content 的生成逻辑，调用上述函数替代统一公式

## 3. 测试

- [x] 3.1 更新 `tests/test_training.py` 中 `test_prepare_sft_data`，验证 OPI 样本的四维分数差异化
- [x] 3.2 新增测试 `test_dimension_profiles_fallback`，验证未知 attack_type 回退到 default profile
- [x] 3.3 新增测试 `test_contradictions_only_on_low_scores`，验证 contradictions 仅在分数 < 0.5 时填充
- [x] 3.4 运行 `python -m unittest tests.test_training -v`，确认全部通过
