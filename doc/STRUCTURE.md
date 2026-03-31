# Repository Structure

This document is the canonical structure map for IntentGuard. Every major code and data surface has a defined home here. New files and directories must be placed according to these boundaries.

## Code Domains

| Directory | Owner / Purpose |
|-----------|----------------|
| `agents/` | Agent strategy implementations (default, react, plan-execute, guard-augmented variants) |
| `runtime/` | Shared execution primitives: model clients, factories, parsers, prompt helpers, function-call handling |
| `guard/` | Normalized Guard subsystem: config, subsystem interface |
| `guardrail/` | Future: higher-level intent-aware middleware and policy engine (Phase 1+) |
| `processors/` | Benchmark adapters and runners (AgentHarm, ASB; future AgentDojo) |
| `phase0/` | Baseline-only orchestration, readiness checks, and scoring helpers |
| `training/` | Future: training-data construction and model-training pipeline (Phase 2+) |
| `evaluation/` | Future: experiment metrics, runners, ablations, and reporting (Phase 3+) |
| `configs/` | Experiment and policy configuration files |
| `scripts/` | CLI entrypoints for running benchmarks, environment checks, and summaries |
| `tests/` | Automated verification (unit + integration) |
| `standalone_agent_env/` | Compatibility namespace only — forwards to canonical modules above |

## Data, Config, and Output Roots

| Path | Purpose |
|------|---------|
| `data/agentharm/` | AgentHarm benchmark source assets (datasets + environments) |
| `data/asb/` | ASB benchmark source assets |
| `data/agentdojo/` | AgentDojo benchmark source assets |
| `data/manifests/` | Shared metadata: source maps, provenance files, dataset manifests |
| `data/guard_training/` | Generated or curated guard-training datasets |
| `configs/` | Experiment configuration files (schema, policy, training, evaluation) |
| `outputs/baseline/` | Phase 0 baseline experiment artifacts |
| `outputs/agentdojo/` | AgentDojo benchmark run outputs |
| `outputs/guard_models/` | Trained guard model checkpoints and metadata |
| `outputs/ablation/` | Ablation study outputs |
| `outputs/final/` | Final paper-ready summaries and reports |

Generated outputs must NOT be written back into `data/` source subtrees.

## Compatibility and Migration

`standalone_agent_env/` is a supported compatibility namespace. It forwards package imports and script entrypoints to canonical root-level modules. It is not a second implementation surface.

### Import mapping

| Legacy import | Canonical module |
|---------------|-----------------|
| `standalone_agent_env.runtime` | `runtime` |
| `standalone_agent_env.agents` | `agents` |
| `standalone_agent_env.processors` | `processors` |
| `standalone_agent_env.guard` | `guard` |

### Script entrypoint mapping

| Legacy entrypoint | Canonical script |
|-------------------|-----------------|
| `python -m standalone_agent_env.scripts.run_agentharm` | `python -m scripts.run_agentharm` |
| `python -m standalone_agent_env.scripts.run_asb` | `python -m scripts.run_asb` |
| `python -m standalone_agent_env.scripts.run_phase0_baselines` | `python -m scripts.run_phase0_baselines` |
| `python -m standalone_agent_env.scripts.summarize_phase0_metrics` | `python -m scripts.summarize_phase0_metrics` |
| `python -m standalone_agent_env.scripts.check_phase0_env` | `python -m scripts.check_phase0_env` |

## Future Directories

`guardrail/`, `training/`, and `evaluation/` are scaffolded but not yet implemented. Their `__init__.py` files declare ownership and intent. Do not add business logic to these directories until the corresponding implementation phase begins.
