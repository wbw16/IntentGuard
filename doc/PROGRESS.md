# IntentGuard 工作进度追踪

> 最后更新：2026-03-31

## 总览

| Phase | 名称 | 状态 | 完成日期 | Commit |
|-------|------|------|----------|--------|
| Phase 0 | 基线实验环境 | ✅ 已完成 | — | `be052c6`, `5ebfe8f` |
| Phase 1 | 结构化意图 Schema | ✅ 已完成 | — | `81f38f2` |
| Phase 2 | 执行前护栏中间件 | ✅ 已完成 | — | `eef77cc` |
| Phase 3 | 训练数据构造流水线 | ✅ 已完成 | 2026-03-31 | `35bad4e` |
| Phase 4 | AgentDojo 本地 Runner | ⬜ 未开始 | — | — |
| Phase 5 | 评测框架与实验执行 | ⬜ 未开始 | — | — |

## Phase 0：基线实验环境 ✅

已有基础设施：
- 7 个 agent 策略（react, sec_react, intentguard, planexecute, sec_planexecute, ipiguard, react_firewall）
- runtime 层（core, modeling, factory, parsers, prompts, guardian_parser）
- guard 子系统（GuardSubsystem, GuardDecision, GuardEvaluationRequest）
- 处理器（AgentHarmProcessor, ASBProcessor）
- 脚本入口（run_agentharm.py, run_asb.py）
- 基线输出（outputs/baseline/）

## Phase 1：结构化意图 Schema ✅

产出物：
- `configs/intent_schema.yaml` — 8 个事实性字段定义
- `runtime/intent_schema.py` — IntentDeclaration dataclass
- `runtime/parsers.py` — extract_intent() 解析器
- `runtime/prompts.py` — INTENTGUARD_REACT_SYSTEM_PROMPT
- `agents/intentguard_agent.py` — IntentGuard agent 基础循环

核心设计：字段不含自我安全评估，全部是可被护卫模型交叉验证的事实性声明。

## Phase 2：执行前护栏中间件 ✅

产出物：
- `configs/decision_types.yaml` — 4 种决策类型 + 阈值
- `configs/policy_rules.yaml` — 4 条策略规则
- `guardrail/__init__.py` — DecisionType, CrossValidationResult, GuardrailDecision, GuardrailMiddleware
- `guardrail/cross_validator.py` — 四维交叉验证引擎
- `guardrail/guard_model_adapter.py` — prompt 构造与 JSON 响应解析
- `guardrail/policy_engine.py` — YAML 策略规则匹配
- `guardrail/decision_maker.py` — 分数+规则→决策映射
- `guardrail/audit_logger.py` — JSONL 审计日志
- `tests/test_guardrail.py` — 24 个测试

核心设计：单次 prompt 完成 4 维交叉验证，策略规则可覆盖分数决策。

## Phase 3：训练数据构造流水线 ✅

产出物：
- `configs/training_config.yaml` — 完整训练配置
- `training/label_schema.py` — TrainingSample, AttackScenario 等数据结构
- `training/data_collector.py` — 从 agentharm/asb/agentdojo 统一采集
- `training/trace_generator.py` — 驱动 agent 执行并收集轨迹
- `training/sample_constructor.py` — 逐步抽取训练样本
- `training/deception_augmentor.py` — 4 种欺骗策略增强
- `training/train_guard.py` — SFT 数据准备 + LoRA/full 微调
- `tests/test_training.py` — 18 个测试

核心设计：意图欺骗增强器自动构造"表面合规的虚假意图"负样本。

## Phase 4：AgentDojo 本地 Runner ⬜

待实现：
- `processors/agentdojo.py` — AgentDojo 处理器
- `scripts/run_agentdojo.py` — 运行入口
- 4 个 suite（banking, slack, travel, workspace）端到端验证

## Phase 5：评测框架与实验执行 ⬜

待实现：
- `evaluation/metrics.py` — ASR, TCR, FPR, Latency, Deception Detection Rate
- `evaluation/eval_runner.py` — 批量实验矩阵（6 agent × 4 benchmark）
- `evaluation/ablation.py` — 6 组消融实验
- `evaluation/report_generator.py` — LaTeX 表格和图表生成

## 测试状态

| 测试文件 | 测试数 | 状态 |
|----------|--------|------|
| tests/test_guardrail.py | 24 | ✅ 全部通过 |
| tests/test_training.py | 18 | ✅ 全部通过 |
| tests/test_guard_subsystem.py | — | ⚠️ 预存在的循环导入问题 |
| tests/test_canonical_layout.py | — | 未验证 |
