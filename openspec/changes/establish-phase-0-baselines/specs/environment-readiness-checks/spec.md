## ADDED Requirements

### Requirement: Phase 0 readiness validation covers baseline prerequisites
The system SHALL provide a Phase 0 readiness command that validates the baseline prerequisites from the repository root before any benchmark run starts. The validation MUST cover required agent strategies, benchmark datasets, runtime imports, and output-root writability for the Phase 0 scope.

#### Scenario: Successful readiness validation
- **WHEN** an operator runs the Phase 0 readiness command from the repository root with the default baseline scope
- **THEN** the system reports that the required `react` and `sec_react` strategies, AgentHarm harmful data, ASB data, runtime imports, and baseline output root are available

### Requirement: Repo-root baseline commands are executable without manual import patching
The system SHALL provide a supported repo-root execution path for the extracted standalone environment so that documented Phase 0 commands do not require manual `PYTHONPATH` edits or ad hoc import patching.

#### Scenario: Supported command invocation
- **WHEN** an operator invokes a documented Phase 0 command from the repository root
- **THEN** the command resolves the runtime, agent, processor, and script imports required for Phase 0 execution without asking the operator to patch module search paths manually

### Requirement: Readiness failures are actionable and non-destructive
If a Phase 0 prerequisite is missing or invalid, the readiness command SHALL fail before benchmark execution begins and SHALL identify each blocking issue with a remediation hint.

#### Scenario: Missing prerequisite
- **WHEN** a required import, dataset file, or mandatory model configuration is missing for the requested Phase 0 run
- **THEN** the readiness command exits with a failure status and records the missing prerequisite plus an actionable remediation note without launching any benchmark jobs
