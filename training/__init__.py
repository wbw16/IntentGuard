"""training — 训练数据构造与模型微调流水线。

模块：
  - label_schema: 标注 Schema（TrainingSample, AttackScenario 等数据结构）
  - data_collector: 从 agentharm/asb/agentdojo 采集攻击场景
  - trace_generator: 驱动 agent 执行场景并收集轨迹
  - sample_constructor: 从轨迹中抽取训练样本
  - deception_augmentor: 自动构造虚假意图变体
  - train_guard: 微调训练入口
"""
