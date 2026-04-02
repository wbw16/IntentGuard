## 1. Canonical Layout Skeleton

- [x] 1.1 Create or confirm the canonical repository roots for experiment code, configs, datasets, scripts, tests, and generated outputs.
- [x] 1.2 Add a documented structure map that declares the canonical home and ownership of each major domain (`agents`, `runtime`, `guard`, `guardrail`, `processors`, `phase0`, `training`, `evaluation`, `configs`, `scripts`, `tests`, `data`, `outputs`).
- [x] 1.3 Identify current files and directories that must be extracted, merged, relocated, or converted into compatibility-only surfaces as part of the migration.

## 2. Codebase Normalization

- [x] 2.1 Reorganize existing code modules into their canonical responsibility boundaries, extracting or merging files where ownership is currently ambiguous.
- [x] 2.2 Scaffold future-phase domains such as `guardrail/`, `training/`, `evaluation/`, and `configs/` in a way that matches the implementation plan without inventing unfinished business logic.
- [x] 2.3 Update imports and internal references so canonical root-level modules are the source of truth rather than duplicated or transitional paths.

## 3. Data, Config, And Output Layout

- [x] 3.1 Normalize the `data/` subtree so source benchmarks, manifests, and guard-training datasets each have stable canonical locations.
- [x] 3.2 Create and document the canonical `configs/` and `outputs/` subtrees for baseline artifacts, benchmark runs, guard models, ablations, and final reports.
- [x] 3.3 Update scripts, processors, and supporting helpers to read from and write to the canonical data/config/output paths.

## 4. Compatibility, Verification, And Documentation

- [x] 4.1 Keep `standalone_agent_env` imports and legacy module execution paths working through thin compatibility shims that forward to canonical modules.
- [x] 4.2 Add regression coverage for canonical imports, compatibility aliases, and normalized path assumptions across scripts or helpers.
- [x] 4.3 Update repository documentation and migration guidance so contributors can tell which paths are canonical and how legacy paths map to them.
