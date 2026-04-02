## ADDED Requirements

### Requirement: Data, configuration, and generated artifacts use stable lifecycle roots
The repository SHALL provide stable top-level roots for source datasets, experiment configuration files, and generated artifacts so future experiment phases can rely on predictable paths.

#### Scenario: Source benchmark data is stored predictably
- **WHEN** the repository stores benchmark input assets for AgentHarm, ASB, AgentDojo, or future guard-training data
- **THEN** those assets reside under documented subtrees of `data/`
- **AND** source datasets are not mixed into generated output directories

#### Scenario: Experiment configurations are stored predictably
- **WHEN** a new experiment requires configuration files for schema, policy, training, or evaluation
- **THEN** those files are placed under the canonical `configs/` root
- **AND** they are not scattered across code directories or script-local locations

### Requirement: Generated experiment outputs are standardized by purpose
The repository SHALL store generated experiment artifacts under documented `outputs/` subtrees that distinguish baseline artifacts, benchmark-specific evaluation outputs, trained guard assets, ablation outputs, and final report outputs.

#### Scenario: Baseline artifacts and final reports remain separate
- **WHEN** the repository writes baseline experiment outputs and final experiment summaries
- **THEN** baseline artifacts are stored under a baseline-specific output subtree
- **AND** final paper-ready summaries are stored under a final-report-specific output subtree instead of overwriting intermediate artifacts

### Requirement: Shared manifests and metadata have a canonical home
The repository SHALL store shared manifests, source maps, and other reusable experiment metadata under a documented canonical metadata area.

#### Scenario: Dataset source map is needed by multiple workflows
- **WHEN** multiple experiment workflows depend on shared dataset provenance or metadata
- **THEN** that metadata is stored in the canonical manifest area under `data/`
- **AND** scripts and processors can reference it without embedding duplicate path logic
