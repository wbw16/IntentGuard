## Why

项目在快速迭代中积累了命名不一致问题：Python 类名使用下划线分隔（`ReAct_Agent`）违反 PEP 8 PascalCase 惯例，变量名存在拼写错误（`guardian_paser_map`），文档文件名混用下划线和中文，`standalone_agent_env/` 兼容层中存在冗余的脚本副本。这些问题增加了新贡献者的认知负担，也让 IDE 自动补全和重构工具效果打折。现在 Phase 3 已完成、Phase 4 尚未开始，是统一规范的最佳窗口期。

## What Changes

- **BREAKING**: 8 个 agent 类名从 `Xxx_Yyy_Agent` 重命名为 `XxxYyyAgent`（PascalCase），例如 `ReAct_Agent` → `ReActAgent`
- **BREAKING**: `guardian_paser_map` 拼写错误修正为 `guardian_parser_map`（`runtime/guardian_parser.py` + `guard/subsystem.py`）
- 文档文件名规范化：`IntentGuard_Implementation_Plan.md` → `implementation-plan.md`，`课题总结.md` → `project-summary.md`
- `standalone_agent_env/scripts/` 下 5 个兼容 shim 脚本与 `tests/test_canonical_layout.py`、`tests/test_phase0.py`、`tests/test_guard_subsystem.py` 中的 `standalone_agent_env` 引用同步更新
- `doc/` 内文档中对重命名项的引用更新
- `agents/__init__.py` 中 `AGENT_BUILDERS` 注册表无需改动（只引用模块路径和 `build_agent` 函数名，不引用类名）

## Capabilities

### New Capabilities

- `naming-convention-enforcement`: 定义并执行 Python 类名 PascalCase、变量名 snake_case、文档文件名 kebab-case 的命名规范，覆盖 agents、runtime、guard 模块

### Modified Capabilities

（无已有 spec 需要修改）

## Impact

- **agents/**: 8 个文件的类定义和 `build_agent()` 中的实例化语句
- **runtime/guardian_parser.py**: `guardian_paser_map` → `guardian_parser_map` 变量名
- **guard/subsystem.py**: 3 处对 `guardian_paser_map` 的引用
- **tests/**: `test_guard_subsystem.py` 中的类名引用；`test_canonical_layout.py` 和 `test_phase0.py` 中的 `standalone_agent_env` 引用保持不变（兼容层仍存在）
- **doc/**: 6 个文档文件中对类名和文件名的引用
- 不影响 `configs/`、`data/`、`training/`、`guardrail/`、`processors/` 的代码逻辑
