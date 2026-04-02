## ADDED Requirements

### Requirement: Agent class names use PascalCase
All agent classes in `agents/` SHALL use PascalCase without underscores. The mapping is:
- `ReAct_Agent` → `ReActAgent`
- `SecReAct_Agent` → `SecReActAgent`
- `IntentGuard_Agent` → `IntentGuardAgent`
- `PlanExecute_Agent` → `PlanExecuteAgent`
- `SecPlanExecute_Agent` → `SecPlanExecuteAgent`
- `IPIGuard_Agent` → `IPIGuardAgent`
- `ReAct_Firewall_Agent` → `ReActFirewallAgent`
- `Default_Agent` → `DefaultAgent`

All references to these class names in test files and other modules MUST be updated accordingly.

#### Scenario: Class definition renamed
- **WHEN** reading any agent file in `agents/`
- **THEN** the class definition uses PascalCase without underscores

#### Scenario: build_agent returns renamed class
- **WHEN** `build_agent()` is called in any agent module
- **THEN** it instantiates and returns the PascalCase-named class

#### Scenario: Test references updated
- **WHEN** test files import or reference agent classes
- **THEN** they use the new PascalCase names

### Requirement: Guardian parser map variable name is correctly spelled
The variable `guardian_paser_map` in `runtime/guardian_parser.py` SHALL be renamed to `guardian_parser_map`. All references in `guard/subsystem.py` MUST be updated.

#### Scenario: Variable definition corrected
- **WHEN** reading `runtime/guardian_parser.py`
- **THEN** the variable is named `guardian_parser_map`

#### Scenario: Import references corrected
- **WHEN** `guard/subsystem.py` imports from `runtime.guardian_parser`
- **THEN** it imports `guardian_parser_map` (not `guardian_paser_map`)

#### Scenario: All usages corrected
- **WHEN** searching the entire codebase for `guardian_paser`
- **THEN** zero matches are found

### Requirement: Documentation filenames use kebab-case
All documentation files in `doc/` SHALL use lowercase kebab-case naming. The mapping is:
- `IntentGuard_Implementation_Plan.md` → `implementation-plan.md`
- `课题总结.md` → `project-summary.md`

#### Scenario: Renamed doc files exist
- **WHEN** listing files in `doc/`
- **THEN** `implementation-plan.md` and `project-summary.md` exist
- **THEN** `IntentGuard_Implementation_Plan.md` and `课题总结.md` do not exist

#### Scenario: Doc cross-references updated
- **WHEN** any document references a renamed file
- **THEN** it uses the new kebab-case filename

### Requirement: No residual old names in codebase
After all renames, a full-text search for any old name (underscore class names, `guardian_paser_map`, old doc filenames) SHALL return zero matches across all `.py` and `.md` files.

#### Scenario: Grep verification passes
- **WHEN** running grep for `ReAct_Agent|IntentGuard_Agent|Default_Agent|IPIGuard_Agent|ReAct_Firewall_Agent|SecReAct_Agent|SecPlanExecute_Agent|PlanExecute_Agent|guardian_paser_map|IntentGuard_Implementation_Plan|课题总结`
- **THEN** zero matches are found in `.py` and `.md` files

### Requirement: All existing tests pass after rename
The test suites `test_guardrail.py` (24 tests) and `test_training.py` (18 tests) MUST pass without modification beyond class name reference updates.

#### Scenario: Guardrail tests pass
- **WHEN** running `python -m pytest tests/test_guardrail.py`
- **THEN** all 24 tests pass

#### Scenario: Training tests pass
- **WHEN** running `python -m pytest tests/test_training.py`
- **THEN** all 18 tests pass
