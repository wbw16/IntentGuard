## ADDED Requirements

### Requirement: IntentGuard agent is registered in the agent registry
`agents/__init__.py` 的 `AGENT_BUILDERS` 字典 SHALL 包含键 `"intentguard"`，其值为 `("agents.intentguard_agent", "build_agent")`，使 `get_agent_builder("intentguard")` 能正常返回 builder 函数。

#### Scenario: get_agent_builder returns intentguard builder
- **WHEN** 调用 `get_agent_builder("intentguard")`
- **THEN** 返回 `agents.intentguard_agent` 模块的 `build_agent` 函数，不抛出异常

#### Scenario: unsupported agent name still raises ValueError
- **WHEN** 调用 `get_agent_builder("nonexistent")`
- **THEN** 抛出 `ValueError`，错误信息包含 `"intentguard"` 在支持列表中

### Requirement: IntentGuard agent env vars are configured in .env
`.env` 文件 SHALL 包含 `STANDALONE_INTENTGUARD_*` 环境变量段，所有值引用 `${DEFAULT_*}` 变量，与其他 agent 段格式一致。必须包含以下变量：`STANDALONE_INTENTGUARD_MODEL_NAME`、`STANDALONE_INTENTGUARD_API_KEY`、`STANDALONE_INTENTGUARD_API_BASE`、`STANDALONE_INTENTGUARD_TEMPERATURE`、`STANDALONE_INTENTGUARD_MODEL_TYPE`、`STANDALONE_INTENTGUARD_MODEL_PATH`、`STANDALONE_INTENTGUARD_MAX_TOKENS`、`STANDALONE_INTENTGUARD_TOP_P`、`STANDALONE_INTENTGUARD_GUARD_MODEL_NAME`、`STANDALONE_INTENTGUARD_GUARD_API_KEY`、`STANDALONE_INTENTGUARD_GUARD_API_BASE`、`STANDALONE_INTENTGUARD_GUARD_TEMPERATURE`、`STANDALONE_INTENTGUARD_GUARD_MODEL_TYPE`、`STANDALONE_INTENTGUARD_GUARD_MODEL_PATH`、`STANDALONE_INTENTGUARD_MAX_TURNS`。

#### Scenario: build_agent uses correct API endpoint
- **WHEN** `.env` 已加载且调用 `build_agent()` from `agents.intentguard_agent`
- **THEN** 创建的 `IntentGuardAgent` 的 `agentic_model.config.api_base` 等于 `DEFAULT_API_BASE` 的值

#### Scenario: guard model uses same API as agentic model
- **WHEN** `.env` 已加载且调用 `build_agent()`
- **THEN** guard model 的 API base 与 agentic model 相同（均来自 `${DEFAULT_GUARD_API_BASE}`）

### Requirement: Training pipeline produces non-empty intent_declaration when using intentguard strategy
当 `TraceGenerator.generate(scenario, "intentguard")` 执行时，返回的 `ExecutionTrace` 中每个 `TraceStep` 的 `intent` 字段 SHALL 为非空字典（包含 `action_type` 等字段），而非 `{}`。

#### Scenario: intent_declaration populated in training samples
- **WHEN** 使用 `intentguard` 策略运行 `run_data_pipeline.py`，且场景中 agent 成功调用了至少一个工具
- **THEN** `data/guard_training/samples.jsonl` 中至少一条样本的 `input.intent_declaration` 为非空字典

#### Scenario: trace_generator uses intent_log branch for intentguard
- **WHEN** `TraceGenerator.generate(scenario, "intentguard")` 执行完毕
- **THEN** 返回的 `ExecutionTrace.steps` 中每个 step 的 `intent` 来自 `intent_log`（4-tuple 的第4个元素），而非 regex fallback
