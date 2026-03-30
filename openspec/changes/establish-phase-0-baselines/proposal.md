## Why

IntentGuard intends to compare new pre-execution guardrails against existing agent strategies, but the repository does not yet define a reproducible Phase 0 baseline workflow. Before implementing intent-aware authorization, we need a trusted starting point that confirms the environment is runnable, reproduces baseline results on the target benchmarks, and captures comparable safety and utility metrics.

## What Changes

- Add a Phase 0 change that formalizes environment readiness checks for the current agent, runtime, and dataset layout.
- Define a baseline execution workflow for `react_agent` and `sec_react_agent` on the Phase 0 benchmark scope described in the implementation plan.
- Standardize the output structure under `outputs/baseline/` so raw run artifacts and summarized metrics are stored in predictable locations.
- Define a metrics summarization step that extracts attack success rate (ASR) and task completion rate (TCR) from baseline experiment outputs into a single machine-readable report.

## Capabilities

### New Capabilities
- `environment-readiness-checks`: Verify that the Python environment, required agent implementations, benchmark datasets, and runtime imports are present before baseline experiments begin.
- `baseline-benchmark-execution`: Reproduce Phase 0 baseline runs for `react_agent` and `sec_react_agent` on the selected AgentHarm and ASB benchmark slices, and persist outputs under `outputs/baseline/`.
- `baseline-metrics-summary`: Aggregate baseline run outputs into a `metrics_summary.json` report that records ASR and TCR by agent and benchmark.

### Modified Capabilities
- None.

## Impact

- Affected code and scripts: `agents/`, `runtime/`, `processors/`, `scripts/`
- Affected data and outputs: `data/agentharm/`, `data/asb/`, `outputs/baseline/`
- Affected workflow: experiment setup, baseline execution, and baseline metrics reporting for future IntentGuard comparisons
