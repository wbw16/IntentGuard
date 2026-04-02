## ADDED Requirements

### Requirement: Legacy import and execution paths remain supported through compatibility shims
The repository SHALL preserve supported legacy import and module-execution paths through explicit compatibility layers while the canonical layout becomes the documented source of truth.

#### Scenario: Legacy namespace import resolves to canonical implementation
- **WHEN** existing code imports a module through the supported `standalone_agent_env` compatibility namespace
- **THEN** the import resolves to the canonical implementation in the normalized layout
- **AND** the repository does not require a second duplicated implementation tree for that module

#### Scenario: Legacy script execution path remains valid
- **WHEN** a user runs a supported legacy module entrypoint such as `python -m standalone_agent_env.scripts.<name>`
- **THEN** the command continues to work against the canonical implementation
- **AND** the normalized layout does not break the documented execution surface during migration

### Requirement: Migration mapping is documented
The repository SHALL document how legacy paths map to canonical homes so contributors can migrate code and references deliberately.

#### Scenario: Contributor updates an old path reference
- **WHEN** a contributor encounters a legacy path in code or documentation
- **THEN** the repository provides a documented mapping to the canonical location
- **AND** the contributor can update or preserve the reference without guessing which path is authoritative

### Requirement: Compatibility shims remain thin forwarding layers
Compatibility shims SHALL forward to canonical modules rather than accumulating new business logic or a separate implementation surface.

#### Scenario: Compatibility layer is inspected during maintenance
- **WHEN** a maintainer reviews a compatibility module or wrapper
- **THEN** the wrapper delegates to canonical modules
- **AND** the repository does not require duplicate changes to keep canonical and compatibility code in sync
