## ADDED Requirements

### Requirement: Baseline metrics summary aggregates ASR and TCR by agent and benchmark
The system SHALL generate `outputs/baseline/metrics_summary.json` after Phase 0 raw outputs are available. The summary MUST contain one entry per agent-and-benchmark baseline run and MUST include at least run status, sample counts, ASR, TCR, and the source artifact path used for scoring.

#### Scenario: Summary generated from completed runs
- **WHEN** Phase 0 raw outputs exist for one or more baseline runs
- **THEN** the system writes `outputs/baseline/metrics_summary.json` with separate ASR/TCR summary entries for each completed agent-and-benchmark combination

### Requirement: Metric definitions are traceable
The metrics summary SHALL publish the benchmark-specific scoring definition or scoring note used to compute ASR and TCR so consumers can understand whether the result is exact, proxy-based, or incomplete.

#### Scenario: Scoring provenance
- **WHEN** the system records a baseline summary entry
- **THEN** that entry includes the scoring method identifier or note that explains how ASR and TCR were derived for the benchmark

### Requirement: Incomplete or unscorable runs are explicit
If a baseline run is missing, malformed, or cannot be scored, the summary SHALL mark that run as incomplete or unscorable and SHALL NOT silently substitute zero-valued metrics.

#### Scenario: Missing or invalid raw artifact
- **WHEN** a baseline output required for scoring is missing or invalid
- **THEN** the corresponding summary entry records a non-success status with an explanation instead of reporting ASR or TCR as if the run had succeeded
