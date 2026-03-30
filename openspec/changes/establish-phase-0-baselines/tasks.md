## 1. Repo-Root Readiness

- [x] 1.1 Add a supported repo-root execution path for the extracted `standalone_agent_env` namespace so Phase 0 commands can import agents, runtime modules, processors, and scripts without manual `PYTHONPATH` changes.
- [x] 1.2 Implement a Phase 0 readiness command that checks required baseline agents, benchmark datasets, runtime imports, writable output directories, and mandatory model configuration, then writes a machine-readable readiness report.
- [x] 1.3 Add verification coverage for readiness success and failure cases, including actionable reporting when imports, datasets, or model configuration are missing.

## 2. Baseline Orchestration

- [x] 2.1 Implement a Phase 0 baseline runner that executes the default `{react, sec_react} x {AgentHarm harmful, ASB OPI}` matrix by reusing the existing benchmark processors.
- [x] 2.2 Standardize Phase 0 raw outputs under `outputs/baseline/` and maintain a run manifest that records benchmark, agent, scope, status, and artifact paths.
- [x] 2.3 Preserve rerun safety by wiring the baseline workflow to skip or resume runs that already have partial or completed output artifacts.

## 3. Metrics Summary

- [x] 3.1 Implement repository-local scoring adapters for AgentHarm harmful and ASB OPI that derive scorable signals from stored run traces and benchmark metadata without relying on missing upstream grading dependencies.
- [x] 3.2 Implement the `outputs/baseline/metrics_summary.json` generator so each baseline entry records run status, sample counts, ASR, TCR, scoring notes, and source artifact paths.
- [x] 3.3 Add verification coverage for completed, incomplete, and unscorable baseline outputs so the metrics summary never silently reports zero-valued results for broken runs.

## 4. Documentation

- [x] 4.1 Update the repository documentation with the canonical Phase 0 commands, expected output layout, and the meaning of the baseline readiness report and metrics summary.
