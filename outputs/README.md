# outputs/

Canonical root for all generated experiment artifacts.

## Subtrees

| Directory | Contents |
|-----------|---------|
| `baseline/` | Phase 0 baseline experiment artifacts (`meta_data.json`, summaries) |
| `agentdojo/` | AgentDojo benchmark run outputs |
| `guard_models/` | Trained guard model checkpoints and associated metadata |
| `ablation/` | Ablation study outputs |
| `final/` | Final paper-ready summaries and reports |

**Rule:** Generated outputs must NOT be written back into `data/` source subtrees.
