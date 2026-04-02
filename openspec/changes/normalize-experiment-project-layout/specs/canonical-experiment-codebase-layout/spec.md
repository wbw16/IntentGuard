## ADDED Requirements

### Requirement: Repository has a documented canonical experiment code layout
The repository SHALL define a canonical code layout at the repository root that assigns clear ownership to experiment modules, including agent strategies, shared runtime code, guard and future guardrail code, benchmark processors, scripts, tests, and future training and evaluation modules.

#### Scenario: Contributor locates canonical homes for code
- **WHEN** a contributor adds or moves an experiment code module
- **THEN** the repository provides a documented canonical directory for that module's responsibility
- **AND** the contributor is not required to infer ownership from legacy aliases or ad hoc file placement

### Requirement: Shared responsibilities are separated by domain
The canonical layout SHALL separate stable responsibility domains so that shared runtime utilities, agent strategies, guard logic, processors, baseline helpers, training modules, evaluation modules, and configuration files do not share ambiguous ownership.

#### Scenario: Runtime code and experiment middleware remain distinct
- **WHEN** a module belongs to shared execution/model/parsing primitives
- **THEN** it is placed under the runtime-owned area rather than under agent-specific or future experiment-middleware directories
- **AND** higher-level guardrail, training, or evaluation code is placed under its own canonical domain instead of expanding runtime indefinitely

### Requirement: Root-level code layout is the source of truth
The repository SHALL treat the canonical root-level layout as the source of truth for experiment code rather than treating compatibility namespaces as equivalent implementations.

#### Scenario: Canonical implementation and compatibility alias coexist
- **WHEN** a module is reachable both through a compatibility namespace and through its canonical root-level path
- **THEN** the canonical root-level path is the documented implementation home
- **AND** the compatibility namespace forwards to that implementation instead of maintaining a separate copy
