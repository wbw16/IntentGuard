## ADDED Requirements

### Requirement: Guard configuration resolves through a shared path
The system SHALL resolve Guard model settings through a shared configuration path instead of duplicating Guard wiring logic in each agent implementation that builds a Guard dependency.

#### Scenario: Multiple agents use the same Guard configuration flow
- **WHEN** two different agents construct their Guard dependency
- **THEN** both agents obtain Guard configuration through the same shared resolver or factory path
- **AND** the resulting Guard instance receives a normalized configuration object

### Requirement: Existing per-agent Guard environment names remain compatible
The shared Guard configuration path SHALL preserve compatibility with the current per-agent environment variable names and default inheritance behavior.

#### Scenario: Guard-specific overrides are absent
- **WHEN** an agent's Guard-specific environment variables are not set
- **THEN** the shared configuration path inherits the corresponding primary model settings for that agent
- **AND** the Guard still builds with the same default relationship that the repository currently expects

#### Scenario: Guard-specific overrides are present
- **WHEN** an agent's Guard-specific environment variables are set
- **THEN** the shared configuration path applies those overrides to the Guard configuration
- **AND** the agent does not need custom per-file wiring logic to honor them

### Requirement: Guard setup failures are reported consistently
The shared Guard configuration path SHALL report unsupported model identifiers, invalid configuration combinations, and other Guard setup failures through a consistent error path across agents.

#### Scenario: Unsupported Guard configuration is requested
- **WHEN** an agent attempts to build a Guard with unsupported or invalid Guard settings
- **THEN** the shared configuration path raises or returns a consistent setup failure
- **AND** different agents surface the same class of failure for the same invalid Guard configuration
