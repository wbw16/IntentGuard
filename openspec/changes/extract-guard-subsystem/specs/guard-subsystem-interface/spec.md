## ADDED Requirements

### Requirement: Guard subsystem exposes normalized evaluation entrypoints
The system SHALL provide a public Guard subsystem API for pre-execution review that accepts normalized evaluation input for both tool-safety checks and alignment checks without requiring callers to select prompt templates, parsers, or parser keys.

#### Scenario: Tool-safety review through the public API
- **WHEN** a caller submits a tool-safety evaluation request with the user request, interaction history, current action, and action description
- **THEN** the Guard subsystem returns a structured decision object for that evaluation
- **AND** the caller is not required to provide prompt-template or parser identifiers

#### Scenario: Alignment review through the public API
- **WHEN** a caller submits an alignment evaluation request with the same normalized context fields
- **THEN** the Guard subsystem returns a structured decision object for alignment review
- **AND** the decision object uses the same top-level contract shape as tool-safety review

### Requirement: Guard decisions provide normalized enforcement and audit fields
The Guard subsystem SHALL return a decision object that includes an explicit allow-or-block result, the evaluation mode, a normalized reason, and raw audit evidence from the underlying guard model response.

#### Scenario: Caller consumes a block decision without parser knowledge
- **WHEN** the Guard subsystem determines that a proposed action must be blocked
- **THEN** the decision object explicitly identifies the outcome as blocked
- **AND** the caller can enforce that block without inspecting parser-specific fields or numeric thresholds

#### Scenario: Audit data is preserved with the normalized decision
- **WHEN** the Guard subsystem completes an evaluation
- **THEN** the returned decision includes the raw guard-model output or equivalent audit payload
- **AND** the decision includes enough normalized metadata to explain how the final enforcement outcome was derived

### Requirement: Guard subsystem normalizes degraded evaluations
The Guard subsystem SHALL return a structured decision even when parsing, normalization, or guard-model evaluation does not produce a clean result.

#### Scenario: Guard evaluation degrades
- **WHEN** the underlying guard response cannot be fully parsed or normalized
- **THEN** the Guard subsystem returns a structured decision instead of an untyped dictionary or bare string
- **AND** the structured decision records that the evaluation degraded and preserves the raw output for diagnosis
