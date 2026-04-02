## 1. Agent 类名重命名（PascalCase）

- [x] 1.1 重命名 `agents/react_agent.py` 中 `ReAct_Agent` → `ReActAgent`（类定义 + `build_agent()` 实例化）
- [x] 1.2 重命名 `agents/sec_react_agent.py` 中 `SecReAct_Agent` → `SecReActAgent`
- [x] 1.3 重命名 `agents/intentguard_agent.py` 中 `IntentGuard_Agent` → `IntentGuardAgent`
- [x] 1.4 重命名 `agents/planexecute_agent.py` 中 `PlanExecute_Agent` → `PlanExecuteAgent`
- [x] 1.5 重命名 `agents/sec_planexecute_agent.py` 中 `SecPlanExecute_Agent` → `SecPlanExecuteAgent`
- [x] 1.6 重命名 `agents/ipiguard_agent.py` 中 `IPIGuard_Agent` → `IPIGuardAgent`
- [x] 1.7 重命名 `agents/react_firewall_agent.py` 中 `ReAct_Firewall_Agent` → `ReActFirewallAgent`
- [x] 1.8 重命名 `agents/default_agent.py` 中 `Default_Agent` → `DefaultAgent`

## 2. 测试文件中类名引用更新

- [x] 2.1 更新 `tests/test_guard_subsystem.py` 中 `ReAct_Firewall_Agent`、`SecPlanExecute_Agent`、`SecReAct_Agent` 的 import 和使用
- [x] 2.2 grep 验证：所有 `.py` 文件中不再存在旧的下划线类名

## 3. 拼写错误修正

- [x] 3.1 `runtime/guardian_parser.py` 中 `guardian_paser_map` → `guardian_parser_map`
- [x] 3.2 `guard/subsystem.py` 中 3 处 `guardian_paser_map` 引用更新（import + 2 处使用）
- [x] 3.3 grep 验证：全项目不再存在 `guardian_paser`

## 4. 文档文件名规范化

- [x] 4.1 `doc/IntentGuard_Implementation_Plan.md` → `doc/implementation-plan.md`
- [x] 4.2 `doc/课题总结.md` → `doc/project-summary.md`
- [x] 4.3 更新 `doc/` 内其他文档中对重命名文件的引用（如有）

## 5. 文档内容中旧名引用更新

- [x] 5.1 更新 `doc/PROGRESS.md` 中对旧类名的引用
- [x] 5.2 更新 `doc/SCRIPTS_GUIDE.md` 中对旧类名的引用
- [x] 5.3 更新 `doc/implementation-plan.md` 中对旧类名的引用
- [x] 5.4 更新 `README.md` 中对旧名的引用（如有）

## 6. 验证

- [x] 6.1 运行 `python -m pytest tests/test_guardrail.py -v`，确认 24 个测试全部通过
- [x] 6.2 运行 `python -m pytest tests/test_training.py -v`，确认 18 个测试全部通过
- [x] 6.3 运行 grep 全局验证：旧类名、`guardian_paser`、旧文档文件名零匹配
