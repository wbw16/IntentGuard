## ADDED Requirements

### Requirement: Secure agents perform pre-execution guard review through the shared interface
Any agent mode that enforces Guard decisions before tool execution SHALL invoke the shared Guard subsystem interface before dispatching the proposed tool call to a runtime, function, or tool object.

#### Scenario: Secure ReAct blocks before tool execution
- **WHEN** a secure ReAct-style agent produces a tool call candidate
- **THEN** it submits the candidate action to the Guard subsystem before attempting the actual tool execution
- **AND** the tool is not executed until the Guard decision allows it

#### Scenario: Secure plan-execute blocks before tool execution
- **WHEN** a secure plan-execute agent reaches a planned tool call
- **THEN** it submits the current planned action to the Guard subsystem before attempting the actual tool execution
- **AND** the tool is not executed until the Guard decision allows it

### Requirement: Secure agents consume normalized Guard decisions
Secure agents SHALL enforce Guard outcomes by consuming the normalized decision contract rather than reading parser-specific fields, raw template output, or hard-coded guard thresholds.

#### Scenario: Blocked decision prevents execution
- **WHEN** the Guard subsystem returns a blocked decision for a proposed tool call
- **THEN** the agent does not execute the tool
- **AND** the agent uses the normalized decision content to produce the next observation, refusal, or retry signal in its own loop

#### Scenario: Allowed decision permits execution
- **WHEN** the Guard subsystem returns an allowed decision for a proposed tool call
- **THEN** the agent proceeds to execute the tool through its existing dispatch path
- **AND** the agent is not required to inspect raw guard parser fields before continuing

### Requirement: Alignment-gated agents use the same Guard decision contract
Any agent mode that uses alignment review instead of risk-rating review SHALL still consume the shared Guard subsystem interface and obey the same normalized allow-or-block contract before tool execution.

#### Scenario: Alignment failure stops execution
- **WHEN** an alignment-gated agent receives a blocked decision from the Guard subsystem
- **THEN** the agent terminates or refuses the unsafe path without executing the proposed tool
- **AND** the refusal path uses the normalized decision output rather than a mode-specific parser result
