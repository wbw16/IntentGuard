## Context

IntentGuard 项目在 Phase 0–3 快速迭代中，命名风格未统一：agent 类名使用 `Xxx_Yyy_Agent` 下划线风格（8 个类），`guardian_parser.py` 中存在 `guardian_paser_map` 拼写错误，`doc/` 下文档文件名混用下划线和中文。项目当前处于 Phase 3→4 间隙，外部依赖方（`standalone_agent_env/` 兼容层、测试文件）数量有限，是执行重命名的最佳时机。

涉及模块：`agents/`（8 个文件）、`runtime/guardian_parser.py`、`guard/subsystem.py`、`doc/`（6 个文件）、`tests/`（3 个文件中的类名引用）。

## Goals / Non-Goals

**Goals:**
- 所有 agent 类名遵循 PEP 8 PascalCase（无下划线）
- 修正 `guardian_paser_map` → `guardian_parser_map` 拼写错误
- 文档文件名统一为 kebab-case
- 所有代码和文档中的引用同步更新
- 全部测试通过

**Non-Goals:**
- 不重命名 Python 模块文件名（`react_agent.py` 等 snake_case 文件名符合 PEP 8，保持不变）
- 不重命名 `standalone_agent_env/` 目录（兼容层，保持向后兼容）
- 不修改 `AGENT_BUILDERS` 中的策略名键（`"react"`, `"sec_react"` 等是用户面向的 CLI 参数，不是类名）
- 不重构代码逻辑，仅做命名变更

## Decisions

1. **类名风格：PascalCase 无下划线**
   - `ReAct_Agent` → `ReActAgent`，`SecReAct_Agent` → `SecReActAgent`，以此类推
   - 理由：PEP 8 标准，IDE 友好，与 `GuardrailMiddleware` 等已有类名一致
   - 替代方案：保留下划线 — 否决，因为与 Python 社区惯例不符

2. **拼写修正直接替换**
   - `guardian_paser_map` → `guardian_parser_map`，全局替换
   - 理由：拼写错误，无需保留旧名

3. **文档文件名 kebab-case**
   - `IntentGuard_Implementation_Plan.md` → `implementation-plan.md`
   - `课题总结.md` → `project-summary.md`
   - 理由：kebab-case 是文档文件名的通用惯例，中文文件名在 CLI 和 CI 中不便

4. **一次性全量替换，不保留旧名别名**
   - 理由：项目尚未发布，无外部消费者需要向后兼容

## Risks / Trade-offs

- **测试中断** → 每个重命名类别（类名、变量名、文档名）分步执行并验证测试
- **遗漏引用** → 使用 grep 全局搜索确认无残留旧名
- **`test_guard_subsystem.py` 预存在循环导入** → 已知问题，不在本次范围内修复，仅更新类名引用
