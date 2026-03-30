# IntentGuard 实验实施计划

> 面向 Claude Code 的逐阶段开发指南
> 基于 `standalone_agent_env/` 实验环境

---

## 全局架构概览

```
standalone_agent_env/
├── agents/                          # 已有 7 个智能体策略
│   ├── react_agent.py
│   ├── sec_react_agent.py
│   ├── ...
│   └── intentguard_agent.py         # [新增] IntentGuard 策略智能体
├── runtime/
│   ├── core.py
│   ├── modeling.py
│   ├── factory.py
│   ├── parsers.py
│   ├── prompts.py
│   ├── guardian_parser.py
│   └── intent_schema.py            # [新增] 结构化意图 Schema 定义
├── guardrail/                       # [新增] 核心护栏中间件目录
│   ├── __init__.py
│   ├── intent_extractor.py          # 意图提取与注入模块
│   ├── cross_validator.py           # 多维交叉验证引擎
│   ├── policy_engine.py             # 策略规则引擎
│   ├── decision_maker.py            # 细粒度决策器
│   ├── audit_logger.py              # 审计日志记录
│   └── guard_model_adapter.py       # 护卫模型适配层
├── training/                        # [新增] 护卫模型训练流水线
│   ├── __init__.py
│   ├── data_collector.py            # 从攻击数据集采集原始样本
│   ├── trace_generator.py           # 多底座调用轨迹生成
│   ├── sample_constructor.py        # 意图-参数-风险-决策样本构造
│   ├── deception_augmentor.py       # 意图欺骗对抗样本增强
│   ├── label_schema.py              # 标注 Schema
│   └── train_guard.py               # 训练入口
├── evaluation/                      # [新增] 评测框架
│   ├── __init__.py
│   ├── metrics.py                   # 指标计算
│   ├── eval_runner.py               # 评测运行器
│   ├── ablation.py                  # 消融实验
│   └── report_generator.py          # 结果报告生成
├── processors/
│   ├── agentharm.py
│   ├── asb.py
│   └── agentdojo.py                 # [新增] AgentDojo 本地 runner
├── data/
│   ├── agentharm/
│   ├── asb/
│   ├── agentdojo/
│   └── guard_training/              # [新增] 护卫模型训练数据
├── scripts/
│   ├── run_agentharm.sh
│   ├── run_asb.sh
│   ├── run_intentguard_eval.py      # [新增] IntentGuard 全量评测入口
│   ├── run_training_pipeline.py     # [新增] 训练流水线入口
│   └── run_ablation.py              # [新增] 消融实验入口
├── configs/                         # [新增] 实验配置
│   ├── intent_schema.yaml
│   ├── policy_rules.yaml
│   ├── eval_config.yaml
│   └── training_config.yaml
└── outputs/
```

---

## Phase 0：环境确认与基线复现（预计 1-2 天）

### 目标
确认现有环境可用，跑通 baseline，建立对照数据。

### Claude Code 任务清单

```
任务 0.1: 环境检查
- 进入项目根目录，运行 `pip list` 确认依赖
- 检查 agents/ 下 7 个策略文件是否完整
- 检查 data/ 下三个数据集是否就位
- 验证 runtime/ 下各模块的 import 关系

任务 0.2: 基线运行
- 用 react_agent 跑 AgentHarm harmful subset，记录输出
- 用 react_agent 跑 ASB OPI 攻击，记录输出
- 用 sec_react_agent 跑同样的两组实验
- 整理输出到 outputs/baseline/ 目录

任务 0.3: 基线指标采集
- 从输出 JSON 中提取：攻击成功率(ASR)、任务完成率(TCR)
- 记录每个 agent × 每个 benchmark 的基线数值
- 保存为 outputs/baseline/metrics_summary.json
```

### 产出物
- `outputs/baseline/` 完整基线数据
- `outputs/baseline/metrics_summary.json` 基线指标

---

## Phase 1：结构化意图 Schema 与协议层增强 ✅ 已完成

### 目标
定义意图 Schema，修改 function call 协议使模型同步生成结构化意图。

### 设计原则（修订）
意图字段不包含任何"自我安全评估"（如 risk_hint、affected_parties），
而是强制模型把隐含的执行语义摊开为**可被护卫模型交叉验证的事实性声明**。
护卫模型通过交叉验证这些声明与实际参数/用户指令/历史轨迹的一致性来判断风险。

### IntentDeclaration 字段定义（v2）

| 字段 | 类型 | 用途 | 护卫模型验证维度 |
|------|------|------|------------------|
| action_type | enum | 操作性质 | 与工具参数交叉验证 |
| target_resource | str | 具体资源标识（路径/地址/URL） | 与工具参数交叉验证 |
| operation_description | str | 精确描述本次调用将执行的操作 | 与工具参数交叉验证 |
| data_source | enum | 输入数据来源 | 追踪数据流入 |
| data_destination | enum | 输出/结果流向 | 追踪数据流出 |
| user_instruction_basis | str | 引用用户原始指令中的依据 | 与用户 query 语义一致性验证 |
| expected_side_effects | str | 执行后环境变化 | 评估不可逆性和影响范围 |
| preceding_dependency | str | 依赖前面哪一步的输出 | 验证任务链逻辑连贯性 |

### 已完成任务

```
任务 1.1: ✅ 创建意图 Schema 配置文件
- configs/intent_schema.yaml — 字段枚举、fallback 策略，全部外置配置
- Schema 定义从 yaml 加载，不硬编码

任务 1.2: ✅ 创建意图 Schema 数据类
- runtime/intent_schema.py — IntentDeclaration dataclass
- 从 configs/intent_schema.yaml 加载字段约束
- to_dict() / from_dict() / validate() / make_fallback()

任务 1.3: ✅ 修改提示词模板注入意图要求
- runtime/prompts.py — 新增 INTENTGUARD_REACT_SYSTEM_PROMPT
- 要求模型每步输出 <intent> 块，含 3 个 few-shot 示例
- 强调字段必须是具体事实性信息，不能是模糊描述

任务 1.4: ✅ 修改解析器以提取意图
- runtime/parsers.py — 新增 extract_intent()
- 解析 <intent> 块为 IntentDeclaration
- 格式错误/缺失走 fallback（保守默认值）

任务 1.5: ✅ 创建 IntentGuard 策略智能体
- agents/intentguard_agent.py — IntentGuard_Agent
- ReAct 循环中每步提取意图 + 护栏评估
- _evaluate_intent() 占位接口，Phase 2 替换为 GuardrailMiddleware
```

### 产出物
- `configs/intent_schema.yaml` — 意图字段定义与约束（外置配置）
- `runtime/intent_schema.py` — IntentDeclaration 数据类
- `runtime/prompts.py` — 增强后的提示词（INTENTGUARD_REACT_SYSTEM_PROMPT）
- `runtime/parsers.py` — 增强后的解析器（extract_intent）
- `agents/intentguard_agent.py` — IntentGuard 策略智能体

---

## Phase 2：执行前护栏中间件（核心模块）（预计 4-5 天）

### 目标
构建外挂式护栏中间件，实现多维交叉验证与细粒度决策。

### Claude Code 任务清单

```
任务 2.1: 创建护栏目录骨架
- 创建 guardrail/ 目录及 __init__.py
- 定义 GuardrailMiddleware 主类接口：
  - evaluate(intent, tool_call, context) -> GuardrailDecision
  - 输入: IntentDeclaration, ToolCallParams, ExecutionContext
  - 输出: GuardrailDecision

任务 2.2: 实现 GuardrailDecision 决策结构
- 在 guardrail/__init__.py 中定义
- decision_type: Enum (ALLOW, DENY, REWRITE, DOWNSCOPE, CONFIRM, REPLACE)
- reason: str                   # 决策理由（可解释性）
- modified_params: dict | None  # REWRITE/DOWNSCOPE 时的修改后参数
- replacement_call: dict | None # REPLACE 时的替代调用
- confidence: float             # 决策置信度
- audit_record: dict            # 完整审计记录

任务 2.3: 实现交叉验证引擎 (cross_validator.py) ★ 核心创新点
- 创建 guardrail/cross_validator.py
- 实现 CrossValidator 类，包含四维验证：
  维度 1: intent_vs_user_query()
    - 将声明意图与原始用户指令做语义一致性检查
    - 检测意图是否超出用户请求范围
  维度 2: intent_vs_history()
    - 将声明意图与历史 function call 轨迹做逻辑连贯性检查
    - 检测是否出现与历史轨迹不一致的突变
  维度 3: intent_vs_params()
    - 将声明意图与当前工具参数做匹配性检查
    - 检测参数中的实际操作是否与声明意图矛盾
  维度 4: holistic_consistency()
    - 综合以上三个维度的结果做整体一致性推理
    - 输出一致性分数和矛盾点列表
- 每个维度输出: ConsistencyResult(score, contradictions, evidence)

任务 2.4: 实现护卫模型适配层 (guard_model_adapter.py)
- 创建 guardrail/guard_model_adapter.py
- 封装护卫模型的调用接口
- 构造验证 prompt：将意图+参数+历史+用户指令拼装为结构化输入
- 解析护卫模型返回的 JSON 判定结果
- 支持不同底座模型（GPT-4o, Claude, Qwen 等）

任务 2.5: 实现策略规则引擎 (policy_engine.py)
- 创建 guardrail/policy_engine.py
- 加载 configs/policy_rules.yaml 中的策略规则
- 实现规则匹配逻辑：
  - 工具级权限规则 (哪些工具需要额外确认)
  - 数据流向规则 (external 发送需要更高审查)
  - 受影响方规则 (涉及第三方时触发确认)
  - 历史频率规则 (短时间内同一工具异常高频调用)

任务 2.6: 实现细粒度决策器 (decision_maker.py)
- 创建 guardrail/decision_maker.py
- 综合 cross_validator 和 policy_engine 的输出
- 实现决策逻辑：
  - 一致性高 + 策略通过 → ALLOW
  - 一致性高 + 策略部分违反 → DOWNSCOPE (缩减参数范围)
  - 一致性中等 + 可修正 → REWRITE (重写参数)
  - 一致性低 + 明显矛盾 → DENY
  - 一致性中等 + 不确定 → CONFIRM (请求用户确认)
  - 检测到更安全的替代方案 → REPLACE

任务 2.7: 实现审计日志 (audit_logger.py)
- 创建 guardrail/audit_logger.py
- 记录每次护栏评估的完整信息：
  - 时间戳、调用 ID、用户原始指令
  - 声明意图、工具参数、历史轨迹摘要
  - 交叉验证各维度分数
  - 最终决策及理由
- 输出为 JSONL 格式，便于后续分析

任务 2.8: 创建策略规则配置
- 创建 configs/policy_rules.yaml
- 定义默认策略规则集
- 包含高危工具清单、敏感操作类型、数据流向约束等

任务 2.9: 集成护栏到 IntentGuard Agent
- 修改 agents/intentguard_agent.py
- 在工具执行前调用 GuardrailMiddleware.evaluate()
- 根据 GuardrailDecision 执行对应动作：
  - ALLOW: 正常执行
  - DENY: 跳过执行，返回拒绝信息
  - REWRITE: 用修改后的参数执行
  - DOWNSCOPE: 用缩减后的参数执行
  - CONFIRM: 模拟用户确认（实验中自动处理）
  - REPLACE: 执行替代调用
```

### 产出物
- `guardrail/` 完整目录，含 7 个模块
- `configs/policy_rules.yaml` 策略配置
- `agents/intentguard_agent.py` 集成护栏的智能体

---

## Phase 3：训练数据构造流水线（预计 3-4 天）

### 目标
基于已有攻击数据集，自动化构造"意图—参数—风险—决策"训练样本。

### Claude Code 任务清单

```
任务 3.1: 实现攻击数据采集器 (data_collector.py)
- 创建 training/data_collector.py
- 从 data/agentharm/ 读取 harmful + benign 样本
- 从 data/asb/ 读取 OPI + DPI 攻击场景
- 从 data/agentdojo/ 读取注入向量
- 统一输出格式: AttackScenario(query, tools, attack_type, expected_behavior)

任务 3.2: 实现多底座调用轨迹生成器 (trace_generator.py)
- 创建 training/trace_generator.py
- 对每个 AttackScenario，使用不同 agent 策略执行：
  - react_agent (无防护基线)
  - sec_react_agent (ToolSafe 防护)
  - intentguard_agent (带意图声明)
- 对每个策略可切换不同 LLM 底座
- 记录完整执行轨迹: 每步的 intent + params + observation
- 输出: ExecutionTrace(steps, final_result, was_attacked)

任务 3.3: 实现样本构造器 (sample_constructor.py)
- 创建 training/sample_constructor.py
- 从 ExecutionTrace 中抽取每一步为独立样本
- 每个样本包含:
  - input: {user_query, intent_declaration, tool_params, call_history}
  - label: {decision_type, risk_level, reason, is_deceptive_intent}
- 正常调用标注为 ALLOW
- 攻击成功的调用标注为 DENY/REWRITE 等
- 边界情况标注为 CONFIRM/DOWNSCOPE

任务 3.4: 实现意图欺骗增强器 (deception_augmentor.py) ★ 关键
- 创建 training/deception_augmentor.py
- 对已有攻击样本，自动构造"表面合规的虚假意图"
- 方法:
  - 取攻击调用的真实参数
  - 用 LLM 生成一个看似合理但与参数矛盾的意图声明
  - 形成 (fake_intent, real_params, real_history) 三元组
- 同时构造正常调用的"正确意图"样本作为正样本
- 确保正负样本比例平衡

任务 3.5: 定义标注 Schema
- 创建 training/label_schema.py
- 定义 TrainingSample 数据类
- 定义标注规范和质量检查逻辑
- 实现样本统计和分布检查工具

任务 3.6: 实现训练入口
- 创建 training/train_guard.py
- 支持用构造的数据微调护卫模型
- 支持 LoRA / full fine-tune 两种模式
- 训练后保存模型到 outputs/guard_models/

任务 3.7: 创建训练配置
- 创建 configs/training_config.yaml
- 定义底座模型选择、学习率、epoch、batch_size
- 定义数据增强参数
- 定义验证集划分比例
```

### 产出物
- `training/` 完整目录，含 6 个模块
- `data/guard_training/` 生成的训练数据
- `configs/training_config.yaml` 训练配置

---

## Phase 4：AgentDojo 本地 Runner 补全（预计 2 天）

### 目标
补全 AgentDojo 的本地执行入口，扩充评测覆盖面。

### Claude Code 任务清单

```
任务 4.1: 实现 AgentDojo 处理器
- 创建 processors/agentdojo.py
- 读取 data/agentdojo/suites/ 下的 environment.yaml
- 读取 injection_vectors.yaml 中的攻击配置
- 构造工具环境和任务实例
- 对接 agents/ 下的智能体接口

任务 4.2: 创建 AgentDojo 运行脚本
- 创建 scripts/run_agentdojo.py
- 支持选择 suite (banking, slack, travel, workspace)
- 支持选择 agent 策略
- 支持选择是否启用注入攻击
- 输出到 outputs/agentdojo/<agent>/<suite>/

任务 4.3: 验证四个 suite 的端到端运行
- 逐个 suite 跑通 react_agent 基线
- 确认输出格式与 AgentHarm/ASB 对齐
```

### 产出物
- `processors/agentdojo.py` — AgentDojo 处理器
- `scripts/run_agentdojo.py` — 运行入口
- `outputs/agentdojo/` — AgentDojo 基线结果

---

## Phase 5：评测框架与实验执行（预计 3-4 天）

### 目标
构建统一评测框架，执行完整对比实验和消融实验。

### Claude Code 任务清单

```
任务 5.1: 实现指标计算模块 (metrics.py)
- 创建 evaluation/metrics.py
- 实现以下指标计算：
  - ASR (Attack Success Rate): 攻击成功率，越低越好
  - TCR (Task Completion Rate): 任务完成率，越高越好
  - FPR (False Positive Rate): 误报率（正常调用被误拦截）
  - Latency Overhead: 护栏引入的额外延迟
  - Deception Detection Rate: 意图欺骗识别率
  - Decision Distribution: 各决策类型的分布统计

任务 5.2: 实现评测运行器 (eval_runner.py)
- 创建 evaluation/eval_runner.py
- 支持批量运行 agent × benchmark × attack_type 组合
- 实验矩阵:
  | Agent               | AgentHarm | ASB-OPI | ASB-DPI | AgentDojo |
  |---------------------|-----------|---------|---------|-----------|
  | react (baseline)    |     ✓     |    ✓    |    ✓    |     ✓     |
  | sec_react (ToolSafe)|     ✓     |    ✓    |    ✓    |     ✓     |
  | intentguard (ours)  |     ✓     |    ✓    |    ✓    |     ✓     |
  | planexecute         |     ✓     |    ✓    |    ✓    |     ✓     |
  | ipiguard            |     ✓     |    ✓    |    ✓    |     ✓     |
  | react_firewall      |     ✓     |    ✓    |    ✓    |     ✓     |
- 自动汇总所有结果

任务 5.3: 实现消融实验 (ablation.py)
- 创建 evaluation/ablation.py
- 消融实验设计:
  A1: IntentGuard 完整版 (full)
  A2: 去掉交叉验证，仅用意图声明 (no_cross_validation)
  A3: 去掉意图声明，仅用参数检查 (no_intent)
  A4: 去掉策略引擎，仅用交叉验证 (no_policy)
  A5: 去掉意图欺骗检测 (no_deception_detection)
  A6: 二元决策替代细粒度决策 (binary_only)
- 每个消融配置对应一个 agent 变体
- 在 ASB-OPI 和 AgentHarm-harmful 上运行

任务 5.4: 实现结果报告生成器 (report_generator.py)
- 创建 evaluation/report_generator.py
- 生成 LaTeX 表格格式的对比结果
- 生成消融实验表格
- 生成决策分布可视化数据
- 输出 Markdown 和 JSON 格式

任务 5.5: 创建评测配置
- 创建 configs/eval_config.yaml
- 定义实验矩阵
- 定义指标计算参数
- 定义输出格式

任务 5.6: 创建一键运行脚本
- 创建 scripts/run_intentguard_eval.py
  - 运行完整对比实验
- 创建 scripts/run_ablation.py
  - 运行消融实验
- 创建 scripts/run_training_pipeline.py
  - 运行训练流水线
```

### 产出物
- `evaluation/` 完整目录
- `configs/eval_config.yaml` 评测配置
- `scripts/` 三个入口脚本
- `outputs/` 完整实验结果

---

## Phase 6：端到端集成与论文数据准备（预计 2 天）

### 目标
全流程打通，生成论文所需的数据、表格和图表。

### Claude Code 任务清单

```
任务 6.1: 端到端冒烟测试
- 从数据构造 → 模型训练 → 护栏部署 → 评测，完整跑一遍
- 用 ASB 的一个 agent (如 financial_analyst_agent) 做小规模验证
- 确认所有模块的接口对齐

任务 6.2: 生成论文主表
- 表1: 各 Agent × 各 Benchmark 的 ASR 和 TCR 对比
- 表2: 消融实验结果
- 表3: 意图欺骗检测专项结果
- 表4: 延迟开销分析

任务 6.3: 生成论文图表数据
- 图1: 系统架构图数据（用于手动绘制）
- 图2: 决策类型分布饼图/柱状图
- 图3: 交叉验证各维度贡献度
- 图4: 不同 LLM 底座下的泛化性能

任务 6.4: Case Study 收集
- 从审计日志中筛选典型案例：
  - 成功识破意图欺骗的案例
  - 细粒度决策（REWRITE/DOWNSCOPE）优于二元决策的案例
  - 交叉验证发现矛盾的案例
- 整理为可呈现的 Case Study 格式

任务 6.5: 输出整理
- 所有结果汇总到 outputs/final/
- 生成 outputs/final/experiment_summary.md
```

### 产出物
- `outputs/final/` — 论文就绪的数据和表格

---

## 开发顺序与依赖关系

```
Phase 0 (基线)
    │
    ▼
Phase 1 (意图 Schema)
    │
    ├──────────────┐
    ▼              ▼
Phase 2 (护栏)   Phase 4 (AgentDojo Runner)
    │              │
    ▼              │
Phase 3 (训练)    │
    │              │
    ├──────────────┘
    ▼
Phase 5 (评测)
    │
    ▼
Phase 6 (集成与论文)
```

Phase 2 和 Phase 4 可以并行。Phase 3 依赖 Phase 2 的护栏接口定义。Phase 5 依赖前面所有 Phase。

---

## Claude Code 使用建议

### 每个 Phase 的工作模式

1. **开始前**：把当前 Phase 的任务清单粘贴给 Claude Code，说"请按照这个任务列表逐步实现"
2. **逐任务推进**：每个任务完成后做一次 commit，保持 git 历史清晰
3. **任务间验证**：每完成 2-3 个任务，跑一次单元测试或冒烟测试
4. **Phase 完成后**：跑完整集成测试，确认与已有模块兼容

### 给 Claude Code 的关键上下文提示

每次新会话时，提供以下上下文：

```
项目根目录: IntentGuard/
实验环境: standalone_agent_env/
当前 Phase: [Phase N]
当前任务: [任务 N.X]
已完成的文件: [列出已创建的文件]
技术约束:
- 所有新文件放在 standalone_agent_env/ 下
- 复用 runtime/ 下的已有模块
- 保持与已有 agents/ 的接口一致
- 配置放 configs/，数据放 data/，输出放 outputs/
```

### 关键技术决策记录

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 护卫模型底座 | 先用 API 模型（GPT-4o-mini / Qwen），后微调 | 快速验证 → 专项优化 |
| 意图传递方式 | function call 参数内嵌 | 不改变已有调用协议结构 |
| 交叉验证实现 | 护卫模型单次推理完成四维验证 | 减少延迟，避免多次模型调用 |
| 训练数据格式 | JSON 样本，SFT 格式 | 兼容主流微调框架 |
| 评测框架 | 自建统一 runner | 确保各 benchmark 指标口径一致 |

---

## 风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|----------|
| 护卫模型推理延迟过高 | 影响 TCR 指标 | 先用小模型验证，延迟作为独立指标报告 |
| 意图欺骗样本质量不足 | 影响检测率 | 用多个 LLM 生成多样化欺骗样本 |
| AgentDojo runner 补全困难 | 减少评测覆盖 | 优先保证 AgentHarm + ASB 两个核心 benchmark |
| 不同 LLM 底座调用格式差异 | 影响轨迹生成 | 在 runtime/modeling.py 做统一适配 |
| 训练数据标注一致性 | 影响模型质量 | 定义明确的标注 Schema + 自动化标注为主 |
