## 1. 注册 IntentGuard Agent

- [x] 1.1 在 `agents/__init__.py` 的 `AGENT_BUILDERS` 字典中添加 `"intentguard": ("agents.intentguard_agent", "build_agent")`
- [x] 1.2 验证：`python -c "from agents import get_agent_builder; b = get_agent_builder('intentguard'); print('OK:', b)"` 无报错

## 2. 补充 .env 环境变量

- [x] 2.1 在 `.env` 末尾追加 `STANDALONE_INTENTGUARD_*` 段（15个变量，复用 `${DEFAULT_*}`），参考其他 agent 段格式
- [x] 2.2 验证：加载 `.env` 后 `os.getenv("STANDALONE_INTENTGUARD_API_BASE")` 返回正确的 API base URL

## 3. 验证端到端

- [x] 3.1 运行 `python -m scripts.run_data_pipeline --max-scenarios 2 --strategy intentguard`，确认至少一条样本的 `input.intent_declaration` 非空
- [x] 3.2 检查 `data/guard_training/samples.jsonl`，确认 `intent_declaration` 包含 `action_type`、`target_resource` 等字段
