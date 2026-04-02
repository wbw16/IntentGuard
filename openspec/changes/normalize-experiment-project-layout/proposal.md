## Why

IntentGuard's repository has grown around extracted baseline code, compatibility shims, and new research modules, but the current layout still mixes canonical experiment code, transitional aliases, benchmark data, and implementation-phase artifacts in ways that make future development harder to reason about. Before the project expands into intent schema, guardrail middleware, training, and evaluation phases, we need a normalized repository structure that matches the experiment plan and gives every code and data surface a clear home.

## What Changes

- Define a canonical experiment-oriented repository layout for code, configs, datasets, scripts, tests, and generated outputs so the repo has one authoritative structure instead of several overlapping ones.
- Reorganize existing code modules by responsibility, including extracting or merging modules where needed so shared runtime, agent strategies, guard logic, benchmark processors, and future experiment components follow consistent boundaries.
- Standardize dataset, manifest, and experiment artifact locations so raw benchmark data, derived training data, baseline outputs, evaluation outputs, and final reports live under predictable roots.
- Preserve a deliberate compatibility layer for legacy imports, entrypoints, and path expectations while the canonical structure becomes the documented source of truth.
- Update project documentation and migration guidance so future changes can build on the normalized layout without reintroducing path drift or duplicate module ownership.

## Capabilities

### New Capabilities
- `canonical-experiment-codebase-layout`: Define the canonical repository structure and module ownership for agent code, shared runtime, guardrail components, training components, evaluation components, scripts, and tests.
- `experiment-data-config-output-layout`: Standardize where benchmark datasets, manifests, configs, generated training samples, baseline artifacts, evaluation outputs, and final experiment reports are stored.
- `legacy-layout-compatibility`: Preserve supported legacy import and execution paths through explicit compatibility shims while the canonical layout becomes the primary documented interface.

### Modified Capabilities
- None.

## Impact

- Affected code and module boundaries: `agents/`, `runtime/`, `guard/`, `processors/`, `phase0/`, `scripts/`, compatibility namespaces, and planned future directories such as `guardrail/`, `training/`, `evaluation/`, and `configs/`
- Affected data and artifact paths: `data/`, `outputs/`, manifests, generated training samples, and benchmark-specific raw output locations
- Affected workflow: imports, script entrypoints, documentation, experiment setup, and future implementation phases that assume a normalized experiment repository
