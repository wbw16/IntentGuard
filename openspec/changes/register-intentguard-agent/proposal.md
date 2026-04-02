## Why

`IntentGuardAgent` 是唯一能在每步工具调用前产出结构化 `<intent>` 声明的 agent，但它既未注册到 `agents/__init__.py`，`.env` 也缺少对应的环境变量段，导致训练数据采集只能用 `react` agent，产出的 `intent_declaration` 全为空，无法训练 Guard 模型的核心能力。

## What Changes

- 在 `agents/__init__.py` 的 `AGENT_BUILDERS` 字典中注册 `"intentguard"` 策略，指向 `agents.intentguard_agent.build_agent`
- 在 `.env` 中补充 `STANDALONE_INTENTGUARD_*` 环境变量段，复用 `DEFAULT_*` 变量（与其他 agent 保持一致）
- 在 `configs/training_config.yaml` 的 `trace_generation.agent_strategies` 中将 `intentguard` 加入默认策略列表

## Capabilities

### New Capabilities

- `intentguard-agent-registration`: 将 IntentGuardAgent 注册为可用 agent 策略，使其可通过 `get_agent_builder("intentguard")` 获取，并在训练数据采集流水线中产出带完整 intent 声明的执行轨迹

### Modified Capabilities

（无现有 spec 需要变更）

## Impact

- `agents/__init__.py` — 新增一行注册
- `.env` — 新增 `STANDALONE_INTENTGUARD_*` 段（约 15 行）
- `configs/training_config.yaml` — `agent_strategies` 列表加入 `intentguard`
- 训练数据质量：`intent_declaration` 从全空变为完整 8 字段结构体，`tool_params` 也将正确填充
