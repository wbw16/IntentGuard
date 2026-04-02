## Context

`agents/__init__.py` 维护一个 `AGENT_BUILDERS` 字典，将策略名映射到 `(module, build_agent)` 二元组，通过 `get_agent_builder(name)` 懒加载。目前注册了 7 种策略（default, react, sec_react, planexecute, sec_planexecute, ipiguard, react_firewall），但 `intentguard_agent.py` 虽然存在完整实现，却未注册。

每个 agent 的运行时配置通过 `STANDALONE_<PREFIX>_*` 环境变量注入，`.env` 中已有其他 7 个 agent 的配置段，`STANDALONE_INTENTGUARD_*` 段缺失，导致 `build_agent()` 使用硬编码默认值（`gpt-4o-mini` + `localhost:8000`）。

`configs/training_config.yaml` 的 `trace_generation.agent_strategies` 当前为 `["react", "intentguard"]`，但因为 `intentguard` 未注册，`TraceGenerator` 在调用时会抛出 `ValueError` 并被静默捕获，实际只用 `react`。

## Goals / Non-Goals

**Goals:**
- 使 `get_agent_builder("intentguard")` 正常工作
- 使 `IntentGuardAgent` 使用与其他 agent 相同的 mimo/claude API 配置
- 使训练数据采集流水线能产出带完整 `intent_declaration` 的样本

**Non-Goals:**
- 修改 `IntentGuardAgent` 的内部逻辑
- 修改 `GuardrailMiddleware` 或 guard 子系统
- 修改 `TraceGenerator` 或 `SampleConstructor`

## Decisions

**决策 1：注册方式与现有 agent 保持一致**

直接在 `AGENT_BUILDERS` 字典中加一行 `"intentguard": ("agents.intentguard_agent", "build_agent")`，与其他 7 个 agent 完全相同的模式。不引入新的注册机制。

**决策 2：`.env` 中 INTENTGUARD 段复用 `${DEFAULT_*}` 变量**

与其他 agent 段保持一致，所有值引用 `${DEFAULT_MODEL_NAME}`、`${DEFAULT_API_KEY}`、`${DEFAULT_API_BASE}`，而不是硬编码。这样切换模型时只需改 `DEFAULT_*` 一处。

**决策 3：`training_config.yaml` 中保留 `intentguard` 在策略列表**

`agent_strategies` 已经包含 `intentguard`，注册后自动生效，无需修改 yaml。但需确认列表顺序（`intentguard` 优先，因为它产出更丰富的数据）。

## Risks / Trade-offs

- **[Risk] IntentGuardAgent 调用 GuardrailMiddleware，会额外消耗 API token（guard model 也会被调用）** → 在 `.env` 中将 `STANDALONE_INTENTGUARD_GUARD_MODE` 设为 `cross_validate`（默认值），这是预期行为；如需节省 token 可改为 `passthrough`
- **[Risk] `intentguard_agent.py` 顶部在模块导入时读取环境变量**（`model_name = os.getenv(...)`），若 `.env` 未加载则使用默认值 → `run_data_pipeline.py` 已在导入 agent 前加载 `.env`，无问题
- **[Risk] `STANDALONE_INTENTGUARD_GUARD_MODE` 未在 `.env` 中设置时默认 `cross_validate`，guard model 会对每步调用发起 LLM 请求** → 数据采集时 API 调用量翻倍；可接受，因为这正是我们要采集的数据

## Migration Plan

1. 编辑 `agents/__init__.py`，加一行注册
2. 编辑 `.env`，追加 `STANDALONE_INTENTGUARD_*` 段
3. 验证：`python -c "from agents import get_agent_builder; get_agent_builder('intentguard')"`
4. 运行 `python -m scripts.run_data_pipeline --max-scenarios 2 --strategy intentguard` 验证 intent 字段非空

回滚：删除 `agents/__init__.py` 中新增的一行，删除 `.env` 中新增的段。
