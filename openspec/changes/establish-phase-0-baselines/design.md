## Context

This repository is an extracted standalone agent experiment environment for future IntentGuard work. Today it already contains agent strategies, shared runtime code, benchmark processors, and local benchmark data, but it does not yet provide a reliable Phase 0 workflow that can be executed end-to-end from the repository root.

Several practical gaps showed up during inspection:

- The codebase still imports modules through the `standalone_agent_env.*` namespace, but the current checkout is rooted at `IntentGuard/`, so direct repo-root imports fail without an additional compatibility layer or import rewrite.
- The existing benchmark entrypoints (`scripts/run_agentharm.py` and `scripts/run_asb.py`) can write raw `meta_data.json` outputs, but they do not provide a single orchestration flow for the full Phase 0 matrix or a canonical `outputs/baseline/` layout.
- The extracted AgentHarm grading files depend on upstream modules such as `utils.grading_utils` that are not present in this repository, so baseline metric extraction cannot rely on the original grading stack as-is.

Phase 0 therefore needs to do more than "run two scripts." It needs a reproducible baseline workflow that validates the environment, executes the planned benchmark matrix, and emits traceable ASR/TCR summaries that later IntentGuard phases can compare against.

## Goals / Non-Goals

**Goals:**

- Make the existing standalone environment runnable from the repository root for the Phase 0 baseline path.
- Add a single, documented Phase 0 workflow that covers readiness checks, baseline execution, and metrics summarization.
- Reuse existing agent builders and benchmark processors instead of rewriting benchmark logic from scratch.
- Standardize baseline artifacts under `outputs/baseline/` so later IntentGuard evaluations can compare against a stable reference.
- Produce machine-readable ASR/TCR summaries with enough provenance to be re-scored or audited later.

**Non-Goals:**

- Implement any Phase 1+ IntentGuard protocol, guardrail, or training components.
- Expand Phase 0 to AgentDojo or other benchmarks not listed in the implementation plan.
- Recreate the full upstream ToolSafe evaluation stack inside this change.
- Redesign the existing agent prompting, parsing, or execution loops beyond what is required to make Phase 0 reproducible.

## Decisions

### 1. Make repo-root execution a first-class requirement

Phase 0 will define a supported way to execute the extracted environment directly from this checkout, without requiring manual `PYTHONPATH` edits. The implementation should favor a thin compatibility layer that preserves the current `standalone_agent_env.*` imports rather than a broad import refactor.

Rationale:

- The current repository, README, and implementation plan all describe the environment as `standalone_agent_env`.
- A compatibility layer is the smallest change that unblocks baseline execution while preserving current file organization.
- A broad import rewrite would create noisy churn before the baseline is even established.

Alternatives considered:

- Rewrite every import to match the current top-level package layout: more invasive and unrelated to the baseline objective.
- Require users to export `PYTHONPATH` manually: workable for one machine, but not reproducible or self-validating.

### 2. Keep benchmark logic in processors and add Phase 0 orchestration at the script layer

The existing `AgentHarmProcessor` and `ASBProcessor` already know how to load local data, construct tool environments, and write run outputs. Phase 0 should add orchestration scripts on top of them instead of embedding cross-benchmark policy directly into processor code.

Planned responsibilities:

- `check_phase0_env`: validate imports, agent availability, dataset presence, and required model configuration.
- `run_phase0_baselines`: execute the planned `{react, sec_react} x {AgentHarm harmful, ASB OPI}` matrix into canonical directories.
- `summarize_phase0_metrics`: read raw outputs and produce a single baseline summary.

Rationale:

- This keeps benchmark-specific loading logic isolated where it already exists.
- It avoids coupling "Phase 0 policy" to every future experiment entrypoint.
- It preserves the ability to run individual benchmark scripts directly for debugging.

Alternatives considered:

- Add Phase 0 branching logic into each processor: would mix orchestration concerns with dataset adapters.
- Encode the workflow only in documentation or shell snippets: hard to validate, resume, or audit.

### 3. Standardize a canonical baseline artifact layout

All Phase 0 outputs should live under `outputs/baseline/`, with per-benchmark raw traces and top-level manifests:

```text
outputs/baseline/
├── readiness/
│   └── report.json
├── agentharm/
│   └── <agent>/harmful/meta_data.json
├── asb/
│   └── <agent>/opi/meta_data.json
├── run_manifest.json
└── metrics_summary.json
```

Rationale:

- Later IntentGuard phases need a single reference root for before/after comparisons.
- Raw benchmark traces and derived summaries should remain co-located but clearly separated.
- A top-level manifest makes partial runs, reruns, and auditing simpler.

Alternatives considered:

- Continue using benchmark-local default paths only: convenient for ad hoc runs, but weak for cross-benchmark baseline management.
- Store only derived metrics: loses the raw evidence needed to debug or re-score later.

### 4. Use repository-local scoring adapters for Phase 0 metrics

Because the extracted repository does not currently include the full upstream grading dependencies, Phase 0 metrics should be computed by local scoring adapters that operate only on repository-resident benchmark metadata and run artifacts. Each adapter must publish its metric definition into the summary output so the reported ASR/TCR is traceable.

Planned approach:

- AgentHarm adapter: derive scorable signals from the sample metadata, target function list, tool-call trace, and final response flow.
- ASB adapter: derive scorable signals from attacker-tool usage, normal-tool usage, and the recorded run trace for each task.
- Summary writer: emit per-benchmark notes that document the scoring method and whether a run is fully scored, proxy scored, or incomplete.

Rationale:

- Phase 0 needs a working baseline now, not after the full evaluation framework is restored.
- Local adapters keep the workflow self-contained and make missing upstream dependencies explicit.
- Publishing the scoring definition prevents overclaiming equivalence with the original benchmark authors' exact graders.

Alternatives considered:

- Block Phase 0 until all upstream grading helpers are reconstructed: slows down the project and delays baseline availability.
- Silent heuristic scoring with no provenance: faster initially, but hard to trust and impossible to compare rigorously later.

### 5. Preserve resumability and scope control

Baseline execution should preserve the current processors' incremental write behavior and expose explicit scope controls for long-running experiments. The default matrix should match the Phase 0 plan, while optional filters can support smoke runs and recovery after interruption.

Rationale:

- Baseline runs are API-dependent and potentially time-consuming.
- The existing processors already support continuing from partially written `meta_data.json`.
- Scope controls help the team validate the pipeline before committing to long full runs.

Alternatives considered:

- Force all-or-nothing runs: simpler, but fragile for research workflows.
- Create separate one-off scripts per agent or benchmark: duplicates orchestration logic.

## Risks / Trade-offs

- [Proxy scoring may differ from upstream benchmark grading] -> Mitigation: include per-benchmark scoring notes, source paths, and status fields in `metrics_summary.json` so later phases can re-score raw traces if stricter graders become available.
- [Compatibility-layer imports may hide deeper packaging issues] -> Mitigation: make repo-root execution an explicit readiness check and fail fast on unresolved imports.
- [Baseline experiments may be slow or costly with remote model APIs] -> Mitigation: support reruns, benchmark filters, and resumable writes rather than assuming a one-shot full run.
- [Canonical output layout may diverge from existing ad hoc outputs] -> Mitigation: keep the new layout additive under `outputs/baseline/` and avoid changing benchmark processors' intrinsic data format.

## Migration Plan

1. Introduce the repo-root execution path and environment readiness check.
2. Add the Phase 0 baseline orchestrator and point it at canonical `outputs/baseline/` directories.
3. Implement local scoring adapters and generate `metrics_summary.json` from raw traces.
4. Update project documentation so Phase 0 becomes the supported way to establish pre-IntentGuard baselines.

Rollback is straightforward because the change is additive: remove the new Phase 0 scripts/helpers and discard `outputs/baseline/` if needed, while leaving the existing agent and processor code paths intact.

## Open Questions

- Should the Phase 0 orchestrator keep ASB's current `task_nums=1` default for fast local baselines, or elevate the default scope once the environment is stable?
- Do we want the readiness report to warn on placeholder API credentials only, or treat them as hard failures for all baseline commands?
