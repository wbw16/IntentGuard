## Context

IntentGuard has already moved beyond a single extracted baseline environment. The repository now contains root-level experiment code (`agents/`, `runtime/`, `processors/`, `phase0/`, `guard/`), a compatibility namespace (`standalone_agent_env/`), benchmark datasets under `data/`, OpenSpec changes, and research planning documents that describe substantial future additions such as `guardrail/`, `training/`, `evaluation/`, `configs/`, and richer `outputs/` trees.

The problem is no longer just "missing directories." The repository currently mixes:

- canonical code modules and compatibility aliases
- source datasets and generated experiment artifacts
- baseline-specific helpers and longer-term research architecture
- current executable surfaces and planned future surfaces

This creates path ambiguity: the README still frames the project as `standalone_agent_env/`, while the actual executable code lives at the repo root and `standalone_agent_env/` acts as a compatibility namespace. Without an explicit normalization pass, each future phase risks adding more one-off files, duplicate boundaries, and path drift.

## Goals / Non-Goals

**Goals:**

- Establish one canonical experiment-oriented repository layout that matches the implementation plan and current code reality.
- Define clear ownership boundaries for agent code, shared runtime, guard and future guardrail code, benchmark processors, training modules, evaluation modules, configs, scripts, tests, datasets, and generated outputs.
- Standardize dataset/config/output roots so future phases can rely on stable paths instead of ad hoc conventions.
- Preserve necessary compatibility for legacy imports and command entrypoints while making the canonical structure the documented source of truth.
- Provide an incremental migration path that allows code extraction, merging, and relocation without forcing a single risky all-at-once rename.

**Non-Goals:**

- Implement all future `guardrail/`, `training/`, or `evaluation/` functionality described in the long-term plan.
- Change benchmark semantics, dataset contents, or scoring rules beyond what is needed to move files into canonical homes.
- Replace current agent algorithms or re-architect runtime behavior beyond what is required by the normalized structure.
- Remove every compatibility shim immediately; this change is about orderly normalization, not sudden breakage.

## Decisions

### 1. Use the repository root as the canonical experiment workspace

The normalized structure will treat the repository root as the source of truth for experiment code and assets. Existing root-level directories such as `agents/`, `runtime/`, `processors/`, `data/`, `scripts/`, `tests/`, `phase0/`, and `guard/` remain canonical. The `standalone_agent_env/` package remains supported, but only as a compatibility namespace that forwards to canonical modules.

Rationale:

- This matches the current executable reality of the repository.
- It avoids a second large migration into another nested package.
- It keeps paths simple for scripts, OpenSpec changes, and future experiment additions.

Alternatives considered:

- Move everything into `standalone_agent_env/` for strict nested-package purity: conceptually tidy, but it would require a broad relocation of already-working root-level modules.
- Introduce a new `src/intentguard/` package: possible long term, but too disruptive for the current experiment-focused repository.

### 2. Normalize code by responsibility, not by implementation phase alone

The canonical layout will separate stable responsibility domains:

- `agents/`: strategy implementations
- `runtime/`: shared execution/model/parsing primitives
- `guard/`: current normalized Guard subsystem
- `guardrail/`: future higher-level intent-aware middleware and policy engine
- `processors/`: benchmark adapters/runners
- `phase0/`: baseline-only orchestration and scoring helpers
- `training/`: training data construction and model-training pipeline
- `evaluation/`: experiment metrics, runners, ablations, and reporting
- `configs/`: experiment configuration files
- `scripts/`: CLI entrypoints
- `tests/`: automated verification

Future-phase directories may be scaffolded before they are fully implemented, but their ownership must be explicit from the start.

Rationale:

- This aligns with the implementation plan while avoiding a flat root full of unrelated modules.
- It clarifies where code extraction and code merging should happen.
- It prevents future features from leaking into `runtime/` or `agents/` by default.

Alternatives considered:

- Keep adding features into existing `runtime/` and `phase0/` directories: faster short term, but it would recreate the same layout ambiguity.
- Organize strictly by research phase (`phase1/`, `phase2/`, ...): easier for a timeline, but worse for long-term maintainability and reuse.

### 3. Standardize data, configs, and outputs as lifecycle roots

The normalized layout will preserve benchmark-local data directories under `data/` while standardizing a complete lifecycle:

- `data/agentharm/`, `data/asb/`, `data/agentdojo/`: source benchmark assets
- `data/manifests/`: source mappings and shared metadata
- `data/guard_training/`: generated or curated guard-training datasets
- `configs/`: experiment and policy configuration files
- `outputs/baseline/`, `outputs/agentdojo/`, `outputs/guard_models/`, `outputs/ablation/`, `outputs/final/`: generated experiment results and reports

Generated outputs must not be mixed back into source dataset roots.

Rationale:

- The implementation plan already assumes stable `configs/`, `data/`, and `outputs/` roots.
- Separating source inputs from generated artifacts reduces accidental churn and makes experiments reproducible.
- Stable output roots are essential for evaluation, archiving, and paper-ready reporting.

Alternatives considered:

- Keep benchmark-specific outputs under each benchmark runner's legacy default path only: convenient locally, but weak for standardized experiments.
- Create a deeply nested `artifacts/` tree for everything: flexible, but less aligned with the current plan and README expectations.

### 4. Make compatibility deliberate, explicit, and temporary

Compatibility shims will remain part of the normalized design, but only as thin forwarding layers:

- `standalone_agent_env.*` import compatibility
- legacy `python -m standalone_agent_env.scripts.*` execution paths
- migration notes that map legacy paths to canonical homes

Compatibility layers must not become a second implementation surface.

Rationale:

- Existing scripts, docs, and experiments already rely on the compatibility namespace.
- A thin forwarding layer allows the layout to improve without breaking active workflows.
- Explicit migration docs reduce future confusion about what is canonical.

Alternatives considered:

- Remove compatibility paths immediately: simpler end state, but too risky for current usage.
- Leave compatibility behavior undocumented: lower effort now, but it guarantees future drift.

### 5. Migrate incrementally with a visible structure plan

The implementation should begin by creating or confirming the canonical directory skeleton, then migrate code and data references in bounded slices, and finally trim obsolete layouts once compatibility is in place. The repository should ship with a written structure map so future contributors can place new files correctly.

Rationale:

- The current repo already contains working code, so migration safety matters more than theoretical neatness.
- A visible structure plan turns this from a one-time cleanup into an enforceable convention.

Alternatives considered:

- Perform a full rename/move in one pass: faster if perfect, but high-risk and difficult to review.

## Risks / Trade-offs

- [Large file moves can cause noisy diffs and import churn] -> Mitigation: migrate by responsibility slice, keep compatibility shims in place, and document canonical homes clearly.
- [Future-phase scaffolding may create empty directories before full implementations exist] -> Mitigation: keep scaffolding minimal and document purpose so placeholders are intentional rather than confusing.
- [Compatibility layers may outlive their usefulness and preserve ambiguity] -> Mitigation: treat compatibility as an explicit layer with migration notes and a future removal path.
- [Standardized output roots may diverge from some existing script defaults] -> Mitigation: update scripts and README together and keep wrapper compatibility for legacy entrypoints.

## Migration Plan

1. Define and document the canonical repository tree, including new roots such as `configs/`, `guardrail/`, `training/`, `evaluation/`, and normalized `outputs/` subtrees.
2. Migrate current code modules into their canonical responsibility boundaries, extracting or merging files where ownership is ambiguous.
3. Normalize dataset, config, and generated artifact paths, including manifest and output conventions.
4. Update imports, script entrypoints, and compatibility shims so legacy paths forward to canonical modules.
5. Add verification coverage and documentation for the canonical structure, then remove redundant path usage where safe.

Rollback is feasible because the migration can preserve compatibility shims and move in slices: if a slice proves too disruptive, the project can pause with the canonical structure partially established while preserving the current execution surface.

## Open Questions

- Should research planning documents such as `课题总结.md` and `IntentGuard_Implementation_Plan.md` remain at the repository root, or move under a future `docs/`/`research/` area as part of the same normalization?
- Do we want to scaffold future directories like `guardrail/`, `training/`, and `evaluation/` immediately, or only create them when the next implementation change begins?
