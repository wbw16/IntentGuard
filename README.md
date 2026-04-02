# IntentGuard

IntentGuard 是一个面向 LLM 智能体工具调用安全的研究项目，实现了基于结构化意图声明与多维交叉验证的预执行防护框架。

核心特性：
- 结构化意图 Schema（8 维事实性声明）嵌入 function call 协议
- 多维交叉验证护栏中间件（intent vs params / user_query / history / holistic）
- 细粒度决策（ALLOW / DENY / MODIFY / CONFIRM）
- 动态攻防驱动的护卫模型训练流水线
- 统一评测框架（AgentHarm + ASB + AgentDojo）

详细实施计划见 [doc/implementation-plan.md](doc/implementation-plan.md)，脚本使用说明见 [doc/SCRIPTS_GUIDE.md](doc/SCRIPTS_GUIDE.md)。

## 目录结构概览

```text
IntentGuard/
├── agents/          # 智能体策略实现
├── runtime/         # 共享执行、模型、解析原语
├── guard/           # Guard 子系统
├── guardrail/       # 意图感知护栏中间件
├── processors/      # Benchmark 适配器和运行器
├── phase0/          # 基线编排与评分辅助
├── training/        # 训练数据构建与模型训练
├── evaluation/      # 指标计算、评测运行、消融实验与报告
├── configs/         # 实验配置文件
├── scripts/         # CLI 入口
├── tests/           # 自动化测试
├── data/            # Benchmark 源数据
│   ├── agentharm/   # AgentHarm 数据集和工具环境
│   ├── asb/         # ASB 数据集
│   ├── agentdojo/   # AgentDojo suite 元数据
│   ├── manifests/   # 共享元数据（source_map.json 等）
│   └── guard_training/  # Guard 训练数据集（生成后写入）
├── outputs/         # 所有生成产物
│   ├── baseline/    # Phase 0 基线实验产物
│   ├── agentdojo/   # AgentDojo 运行产物
│   ├── guard_models/# 训练后的 Guard 模型
│   ├── ablation/    # 消融实验产物
│   └── final/       # 最终报告
└── standalone_agent_env/  # 兼容命名空间（转发到上述规范模块）
```

## 快速开始

### 1. 模型配置

每个智能体文件顶部包含配置区，可通过环境变量覆盖。例如 `react_agent.py` 对应的变量前缀是 `STANDALONE_REACT_`，包括：

- `STANDALONE_REACT_MODEL_NAME`
- `STANDALONE_REACT_API_KEY`
- `STANDALONE_REACT_API_BASE`
- `STANDALONE_REACT_TEMPERATURE`

Guard 使用 `*_GUARD_*` 后缀，例如 `STANDALONE_REACT_GUARD_MODEL_NAME`。

推荐将配置写入 `.env` 文件（`load_repo_env()` 会自动加载）。

### 2. 运行 AgentHarm

```bash
python -m scripts.run_agentharm --agent react --subset harmful
```

参数说明：
- `--agent`：策略名，如 `react`、`sec_react`、`planexecute`
- `--subset`：`harmful`、`benign` 或 `attack`
- `--output`：可选，指定输出目录；默认写入 `outputs/agentdojo/<agent>/<subset>/`

### 3. 运行 ASB

```bash
python -m scripts.run_asb --agent sec_react --attack-type OPI --task-nums 1
```

参数说明：
- `--agent`：策略名
- `--attack-type`：`OPI` 或 `DPI`
- `--task-nums`：每个 ASB agent 保留的任务数
- `--output`：可选，默认写入 `outputs/agentdojo/<agent>/<attack_type>/`

### 4. 运行 Phase 0 基线

```bash
python -m scripts.check_phase0_env
python -m scripts.run_phase0_baselines
python -m scripts.summarize_phase0_metrics
```

标准产物结构：

```text
outputs/baseline/
├── readiness/report.json
├── agentharm/<agent>/harmful/meta_data.json
├── asb/<agent>/opi/meta_data.json
├── run_manifest.json
└── metrics_summary.json
```

### 5. 运行 AgentDojo

```bash
python -m scripts.run_agentdojo --agent intentguard --suite banking --attack-mode injection
```

### 6. 训练数据构造

```bash
# 全量采集（149 场景 → 411 训练样本）
python -m scripts.run_data_pipeline --max-scenarios 50 --strategy intentguard
```

输出到 `data/guard_training/samples_{model_name}.jsonl` 和 `sft_data_{model_name}.jsonl`。

### 7. 评测与消融

```bash
# 完整对比实验
python -m scripts.run_intentguard_eval

# 消融实验
python -m scripts.run_ablation
```

## 实施进度

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 0 | 环境确认与基线复现 | ✅ 已完成 |
| Phase 1 | 结构化意图 Schema | ✅ 已完成 |
| Phase 2 | 执行前护栏中间件 | ✅ 已完成 |
| Phase 3 | 训练数据构造流水线 | ✅ 已完成 |
| Phase 4 | AgentDojo 本地 Runner | ✅ 已完成 |
| Phase 5 | 评测框架与实验执行 | ✅ 已完成 |
| Phase 6 | 端到端集成与论文数据 | 待开始 |

## 智能体列表

| 策略名 | 文件 | 安全增强 | 说明 |
|--------|------|----------|------|
| `default` | `agents/default_agent.py` | 可选 | 最轻量基线，适合自定义消息流 |
| `react` | `agents/react_agent.py` | 无 | 标准 ReAct 循环 |
| `sec_react` | `agents/sec_react_agent.py` | 是 | ReAct + guardian 安全校验 |
| `planexecute` | `agents/planexecute_agent.py` | 无 | 先规划后执行 |
| `sec_planexecute` | `agents/sec_planexecute_agent.py` | 是 | 安全增强版 Plan-Execute |
| `ipiguard` | `agents/ipiguard_agent.py` | 是 | DAG 拓扑执行，需要 `networkx` |
| `react_firewall` | `agents/react_firewall_agent.py` | 是 | 提示词防火墙防御变体 |
| `intentguard` | `agents/intentguard_agent.py` | 是 | 结构化意图声明 + 多维交叉验证护栏 |

## Guard 子系统

`guard/` 是 Guard 的规范主目录，提供统一的评估请求/决策接口。`sec_react`、`sec_planexecute`、`react_firewall` 均通过共享 Guard 接口执行工具前校验。

## 兼容路径

`standalone_agent_env/` 是薄转发层，保留以下兼容路径：

**包导入兼容：**
```python
import standalone_agent_env.runtime   # → runtime
import standalone_agent_env.agents    # → agents
import standalone_agent_env.processors  # → processors
import standalone_agent_env.guard     # → guard
```

**脚本入口兼容：**
```bash
python -m standalone_agent_env.scripts.run_agentharm   # → scripts.run_agentharm
python -m standalone_agent_env.scripts.run_asb          # → scripts.run_asb
python -m standalone_agent_env.scripts.run_phase0_baselines
python -m standalone_agent_env.scripts.summarize_phase0_metrics
python -m standalone_agent_env.scripts.check_phase0_env
```

兼容路径不会消失，但新代码应优先使用规范路径。迁移映射详见 [STRUCTURE.md](STRUCTURE.md)。

## 数据集概览

| 数据集 | 路径 | 状态 |
|--------|------|------|
| AgentHarm | `data/agentharm/` | 可直接运行（176 harmful + 176 benign 样本） |
| ASB | `data/asb/` | 可直接运行（10 个领域 agent，51 个任务） |
| AgentDojo | `data/agentdojo/` | 可直接运行（4 suite, 39 注入向量） |

数据来源映射见 `data/manifests/source_map.json`。
