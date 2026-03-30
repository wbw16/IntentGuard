## ADDED Requirements

### Requirement: Phase 0 baseline runner covers the planned benchmark matrix
The system SHALL provide a Phase 0 baseline runner that supports the default experiment matrix described in the implementation plan: `react` and `sec_react` on AgentHarm harmful and ASB OPI.

#### Scenario: Default matrix execution
- **WHEN** an operator runs the Phase 0 baseline runner with default settings
- **THEN** the runner schedules baseline jobs for AgentHarm harmful and ASB OPI for both `react` and `sec_react`

### Requirement: Baseline raw outputs use a canonical directory layout
The baseline runner SHALL store raw Phase 0 outputs under `outputs/baseline/` using a deterministic benchmark-and-agent directory structure so later phases can compare against the same reference data.

#### Scenario: Canonical baseline output paths
- **WHEN** a Phase 0 benchmark run completes
- **THEN** the run writes its raw trace artifact to a path under `outputs/baseline/<benchmark>/<agent>/<scope>/` and records the completed run in the baseline manifest

### Requirement: Baseline execution preserves progress across reruns
The Phase 0 baseline workflow SHALL support recovery after interruption by preserving completed raw outputs and skipping or resuming already-started work instead of forcing all runs to restart from scratch.

#### Scenario: Resume after interruption
- **WHEN** an operator reruns the Phase 0 baseline workflow after one or more output directories already contain partial or completed traces
- **THEN** the workflow reuses the existing progress for those runs and only executes the remaining or incomplete work
