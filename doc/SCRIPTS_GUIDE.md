# 系统脚本与模块运行说明

## 目录结构总览

```
IntentGuard/
├── scripts/          # CLI 入口脚本
├── agents/           # 8 个智能体策略
├── runtime/          # 共享执行基础设施
├── guard/            # 护卫模型子系统
├── guardrail/        # 意图感知护栏中间件
├── training/         # 训练数据构造流水线
├── processors/       # 基准测试适配器
├── phase0/           # 基线实验编排
├── evaluation/       # 评测框架
├── configs/          # 配置文件
├── data/             # 数据集
└── outputs/          # 实验输出
```

---

## 一、CLI 脚本（scripts/）

### 1. run_agentharm.py — AgentHarm 基准测试

```bash
python -m scripts.run_agentharm --agent <策略名> --subset <子集> [--output <输出目录>]
```

| 参数 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| `--agent` | react, sec_react, intentguard, planexecute, ... | react | 智能体策略 |
| `--subset` | harmful, benign, attack | harmful | 数据子集 |
| `--output` | 任意路径 | outputs/agentdojo/{agent}/{subset} | 输出目录 |

输出：`meta_data.json`，包含每个样本的 messages, env_info, meta_sample, logs。

### 2. run_asb.py — ASB 基准测试

```bash
python -m scripts.run_asb --agent <策略名> --attack-type <类型> [--task-nums <N>] [--output <输出目录>]
```

| 参数 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| `--agent` | react, sec_react, intentguard, ... | sec_react | 智能体策略 |
| `--attack-type` | OPI, DPI | OPI | 攻击注入方式 |
| `--task-nums` | 正整数 | 1 | 每个领域保留的任务数 |
| `--output` | 任意路径 | outputs/agentdojo/{agent}/{attack_type} | 输出目录 |

- OPI（Output Prompt Injection）：攻击指令注入到工具输出侧
- DPI（Direct Prompt Injection）：攻击指令注入到用户请求侧

### 3. run_phase0_baselines.py — Phase 0 基线批量运行

```bash
python -m scripts.run_phase0_baselines
```

批量运行 react + sec_react 在 agentharm + asb 上的基线实验。

### 4. check_phase0_env.py — 环境就绪检查

```bash
python -m scripts.check_phase0_env
```

检查运行时依赖、agent 注册、数据集存在性、输出目录权限、模型配置。

### 5. summarize_phase0_metrics.py — 基线指标汇总

```bash
python -m scripts.summarize_phase0_metrics
```

汇总 Phase 0 基线实验的指标结果。

### 6. run_agentdojo.py — AgentDojo 基准测试

```bash
python -m scripts.run_agentdojo --agent <策略名> --suite <suite名> [--attack-mode <模式>] [--output <输出目录>]
```

| 参数 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| `--agent` | react, intentguard, ... | react | 智能体策略 |
| `--suite` | banking, slack, travel, workspace | banking | AgentDojo suite |
| `--attack-mode` | injection, benign | injection | 攻击模式 |
| `--output` | 任意路径 | outputs/agentdojo/{agent}/{suite} | 输出目录 |

4 个 suite 共 39 个注入向量（banking: 4, slack: 6, travel: 13, workspace: 16）。

### 7. run_data_pipeline.py — 训练数据构造流水线

```bash
python -m scripts.run_data_pipeline [--max-scenarios <N>] [--strategy <策略名>]
```

| 参数 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| `--max-scenarios` | 正整数 | 3 | 每类场景最大数量 |
| `--strategy` | react, intentguard, ... | intentguard | 智能体策略 |

端到端流水线：DataCollector → TraceGenerator → SampleConstructor → DeceptionAugmentor → GuardTrainer.save_samples + prepare_sft_data。

输出文件名包含模型名称（从 .env 的 `DEFAULT_MODEL_NAME` 获取），支持多模型数据生成：
- `data/guard_training/samples_{model_name}.jsonl`
- `data/guard_training/sft_data_{model_name}.jsonl`

### 8. run_intentguard_eval.py — IntentGuard 全量评测

```bash
python -m scripts.run_intentguard_eval [--agents <列表>] [--benchmarks <列表>]
```

运行完整 agent × benchmark 对比实验矩阵，输出到 `outputs/eval/`。

### 9. run_ablation.py — 消融实验

```bash
python -m scripts.run_ablation [--variants <列表>] [--benchmarks <列表>]
```

5 个消融变体：no_cross_validation, no_intent, no_policy, no_deception_detection, binary_only。

---

## 二、智能体策略（agents/）

| 模块 | 类名 | 说明 |
|------|------|------|
| react_agent.py | ReActAgent | 标准 ReAct（Thought→Action→Observation） |
| sec_react_agent.py | SecReActAgent | ReAct + 工具执行前 guard 安全校验 |
| intentguard_agent.py | IntentGuardAgent | ReAct + 结构化意图声明 + 护栏中间件 |
| react_firewall_agent.py | ReActFirewallAgent | ReAct + alignment 对齐检查 |
| ipiguard_agent.py | IPIGuardAgent | DAG 依赖图 + guard 校验 |
| planexecute_agent.py | PlanExecuteAgent | 先规划后执行策略 |
| sec_planexecute_agent.py | SecPlanExecuteAgent | 规划执行 + guard 校验 |

每个 agent 都有 `build_agent()` 工厂函数，通过环境变量配置模型参数：

```bash
# 以 intentguard 为例
export STANDALONE_INTENTGUARD_MODEL_NAME=gpt-4o-mini
export STANDALONE_INTENTGUARD_API_KEY=your-key
export STANDALONE_INTENTGUARD_API_BASE=http://localhost:8000/v1
export STANDALONE_INTENTGUARD_MODEL_TYPE=api
export STANDALONE_INTENTGUARD_GUARD_MODEL_NAME=gpt-4o-mini
export STANDALONE_INTENTGUARD_GUARD_MODE=cross_validate  # cross_validate | passthrough
```

---

## 三、护栏中间件（guardrail/）

### 核心流程

```
IntentDeclaration + tool_params + query + history
  → GuardrailMiddleware.evaluate()
    → CrossValidator（4 维交叉验证，调用 guard model）
    → PolicyEngine（匹配 policy_rules.yaml）
    → DecisionMaker（综合分数+规则→决策）
    → AuditLogger（写 JSONL）
  → GuardrailDecision (ALLOW/DENY/MODIFY/CONFIRM)
```

### 模块说明

| 模块 | 说明 |
|------|------|
| `__init__.py` | 数据结构：DecisionType, DimensionScore, CrossValidationResult, GuardrailDecision, GuardrailMiddleware |
| cross_validator.py | 四维交叉验证引擎，复用 GuardSubsystem 做模型调用 |
| guard_model_adapter.py | 构造交叉验证 prompt + 解析 JSON 响应 |
| policy_engine.py | 从 policy_rules.yaml 加载规则并匹配意图字段 |
| decision_maker.py | 从 decision_types.yaml 加载阈值，映射分数→决策 |
| audit_logger.py | JSONL 审计日志，输出到 outputs/guardrail_audit/ |

### 配置文件

- `configs/decision_types.yaml` — 决策类型和阈值（可随时修改）
- `configs/policy_rules.yaml` — 策略规则（按 priority 排序匹配）

---

## 四、训练流水线（training/）

### 完整流程（推荐使用一键脚本）

```bash
# 一键运行完整流水线（使用 .env 中配置的默认模型）
python -m scripts.run_data_pipeline --max-scenarios 50 --strategy intentguard

# 输出文件（文件名自动包含模型名称）：
# data/guard_training/samples_{model_name}.jsonl
# data/guard_training/sft_data_{model_name}.jsonl
```

### 使用其他模型生成训练数据

通过环境变量覆盖即可切换模型，**无需修改 .env 文件**：

```bash
# 方式一：单个模型运行
DEFAULT_MODEL_NAME="deepseek-ai/DeepSeek-V3.2" \
STANDALONE_INTENTGUARD_MODEL_NAME="deepseek-ai/DeepSeek-V3.2" \
python -m scripts.run_data_pipeline --max-scenarios 50 --strategy intentguard

# 方式二：多个模型并行运行（后台执行，互不干扰）
for model in "tencent/Hunyuan-A13B-Instruct" "THUDM/GLM-Z1-32B-0414" "deepseek-ai/DeepSeek-V3.2"; do
  DEFAULT_MODEL_NAME="$model" \
  STANDALONE_INTENTGUARD_MODEL_NAME="$model" \
  python -m scripts.run_data_pipeline --max-scenarios 50 --strategy intentguard &
done
wait  # 等待所有后台进程完成
```

说明：
- `DEFAULT_MODEL_NAME` 控制输出文件名中的模型标签
- `STANDALONE_INTENTGUARD_MODEL_NAME` 控制实际调用的模型
- 两者需保持一致
- 如果使用不同的 API 地址/密钥，还需覆盖 `STANDALONE_INTENTGUARD_API_BASE` 和 `STANDALONE_INTENTGUARD_API_KEY`
- 每个模型的输出文件独立命名，不会互相覆盖

### 已生成的训练数据统计

| 模型 | 样本数 | ALLOW | DENY | CONFIRM | 欺骗变体 | 数据质量评价 |
|------|--------|-------|------|---------|----------|-------------|
| Qwen/Qwen3-VL-32B-Instruct | 411 | 290 | 66 | 55 | 44 | 产出最多，三类标签均衡 |
| tencent/Hunyuan-A13B-Instruct | 355 | 227 | 75 | 53 | 50 | DENY 比例高，欺骗变体丰富 |
| THUDM/GLM-Z1-32B-0414 | 226 | 168 | 42 | 16 | 28 | OPI 场景覆盖好 |
| inclusionAI/Ring-flash-2.0 | 152 | 134 | 18 | 0 | 12 | 偏保守，DENY 较少 |
| deepseek-ai/DeepSeek-V3.2 | 149 | 72 | 45 | 32 | 30 | DENY 占比 30%，攻击敏感度高 |
| claude-sonnet-4-6 | 10 | — | — | — | — | 强模型拒绝执行 harmful 场景 |
| stepfun-ai/Step-3.5-Flash | 9 | 9 | 0 | 0 | 0 | 几乎无有效样本，不推荐 |
| **合计** | **1312** | | | | **164** | |

数据文件位于 `data/guard_training/`：
```
samples_{model_tag}.jsonl      — 训练样本（每行一个 JSON 对象）
sft_data_{model_tag}.jsonl     — SFT 格式数据（带差异化四维交叉验证分数）
```

### 模型选择建议

- **推荐用于数据生成的模型**：Qwen3-VL-32B、Hunyuan-A13B、GLM-Z1-32B — 产出量大、标签分布均衡
- **不推荐的模型**：claude-sonnet-4-6（拒绝执行 harmful 场景）、Step-3.5-Flash（几乎无有效输出）
- **弱模型更适合生成 DENY 样本**：弱模型会执行 harmful 工具调用，从而产生 DENY 标签的训练数据
- **多模型混合**：建议使用 3+ 个不同模型生成数据，提升训练数据多样性

### 分步运行

```bash
# 1. 采集攻击场景
python -c "
from training.data_collector import DataCollector
dc = DataCollector()
scenarios = dc.collect_all()
print(f'Collected {len(scenarios)} scenarios')
"

# 2. 生成执行轨迹（需要配置好 agent 模型）
python -c "
from training.trace_generator import TraceGenerator
from training.data_collector import DataCollector
dc = DataCollector()
scenarios = dc.collect_agentharm('harmful')[:5]
tg = TraceGenerator()
traces = tg.generate_batch(scenarios, ['react'])
print(f'Generated {len(traces)} traces')
"

# 3. 构造训练样本
python -c "
from training.sample_constructor import SampleConstructor
# ... 从 traces 构造 samples
"

# 4. 欺骗增强
python -c "
from training.deception_augmentor import DeceptionAugmentor
aug = DeceptionAugmentor()
augmented = aug.augment(samples)
"

# 5. 保存 + 验证 + 准备 SFT 数据
python -c "
from training.train_guard import GuardTrainer
trainer = GuardTrainer()
trainer.save_samples(samples)
report = trainer.validate_dataset(samples)
trainer.prepare_sft_data(samples)
"

# 6. 微调（需要 GPU + transformers + peft）
python -c "
from training.train_guard import GuardTrainer
trainer = GuardTrainer()
result = trainer.train()
print(result)
"
```

### 模块说明

| 模块 | 说明 |
|------|------|
| label_schema.py | 数据结构：TrainingSample, AttackScenario, ExecutionTrace + 质量检查 |
| data_collector.py | 从 agentharm/asb/agentdojo 统一采集 AttackScenario |
| trace_generator.py | 驱动 agent 执行场景，收集 ExecutionTrace |
| sample_constructor.py | 从轨迹每步抽取 TrainingSample，自动标注 |
| deception_augmentor.py | 4 种欺骗策略生成虚假意图变体 |
| train_guard.py | 样本管理 + SFT 数据准备 + LoRA/full 微调 |

---

## 五、运行时基础设施（runtime/）

| 模块 | 说明 |
|------|------|
| core.py | AgentCore — 最小对话执行器（管理消息历史 + 调用模型） |
| modeling.py | RuntimeModelConfig, StandaloneModel（支持 api/vLLM/analysis 三种后端） |
| factory.py | create_model_from_config(), create_guard_from_env() 工厂函数 |
| intent_schema.py | IntentDeclaration dataclass + 从 YAML 加载字段约束 |
| parsers.py | extract_intent(), extract_tool_params_react/planexecute() |
| prompts.py | 各策略的系统提示词模板 + guard 模板 |
| guardian_parser.py | 多种 guard 模型输出格式解析器 |

---

## 五点五、评测框架（evaluation/）

### 核心流程

```
EvalRunner.build_run_specs()  → agent × benchmark 实验矩阵
  → EvalRunner.run_single()  → 分发到对应 Processor
    → compute_metrics_from_meta()  → EvalMetrics
      → ReportGenerator  → Markdown + JSON 报告
```

### 模块说明

| 模块 | 说明 |
|------|------|
| metrics.py | EvalMetrics dataclass + 从 meta_data 计算 ASR/TCR/FPR/延迟/欺骗检测率 |
| eval_runner.py | 实验矩阵构建 + 批量运行 + 结果汇总 |
| ablation.py | 5 个消融变体，通过环境变量覆盖实现配置切换 |
| report_generator.py | 对比表格 + 消融表格 + 决策分布表格 + 完整报告 |

### 指标说明

| 指标 | 说明 | 方向 |
|------|------|------|
| ASR | 攻击成功率 | 越低越好 |
| TCR | 任务完成率 | 越高越好 |
| FPR | 误报率（正常调用被误拦截） | 越低越好 |
| Latency | 护栏引入的额外延迟 | 越低越好 |
| DDR | 意图欺骗识别率 | 越高越好 |

### 配置文件

- `configs/eval_config.yaml` — 实验矩阵、指标参数、输出格式

---

## 六、测试

```bash
# 运行护栏中间件测试（24 个）
python -m pytest tests/test_guardrail.py -v

# 运行训练流水线测试（18 个）
python -m pytest tests/test_training.py -v

# 运行 AgentDojo 处理器测试（12 个）
python -m pytest tests/test_agentdojo.py -v

# 运行评测框架测试（23 个）
python -m pytest tests/test_evaluation.py -v

# 运行全部测试（排除已知循环导入问题）
python -m pytest tests/ -v --ignore=tests/test_guard_subsystem.py
```

---

## 七、环境变量速查

| 变量 | 说明 |
|------|------|
| `DEFAULT_API_BASE` | 默认 API 地址（被 STANDALONE_*_API_BASE 引用） |
| `DEFAULT_API_KEY` | 默认 API 密钥 |
| `DEFAULT_MODEL_NAME` | 默认模型名称（用于训练数据输出文件命名） |
| `STANDALONE_{AGENT}_MODEL_NAME` | agent 模型名称 |
| `STANDALONE_{AGENT}_API_KEY` | API 密钥 |
| `STANDALONE_{AGENT}_API_BASE` | API 地址 |
| `STANDALONE_{AGENT}_MODEL_TYPE` | api / analysis / vllm |
| `STANDALONE_{AGENT}_GUARD_MODEL_NAME` | guard 模型名称 |
| `STANDALONE_{AGENT}_GUARD_MODE` | cross_validate / passthrough |
| `INTENT_SCHEMA_CONFIG` | 意图 schema 配置路径覆盖 |
| `DECISION_TYPES_CONFIG` | 决策类型配置路径覆盖 |
| `POLICY_RULES_CONFIG` | 策略规则配置路径覆盖 |
| `TRAINING_CONFIG` | 训练配置路径覆盖 |
| `INTENTGUARD_AUTO_CONFIRM` | CONFIRM 决策自动处理（deny/allow） |

其中 `{AGENT}` 可以是：REACT, SEC_REACT, INTENTGUARD, PLANEXECUTE, SEC_PLANEXECUTE, IPIGUARD, REACT_FIREWALL。

`.env` 文件支持 `${VAR}` 变量引用语法，例如：
```
DEFAULT_API_BASE=https://api.example.com/v1
STANDALONE_INTENTGUARD_API_BASE=${DEFAULT_API_BASE}
```
