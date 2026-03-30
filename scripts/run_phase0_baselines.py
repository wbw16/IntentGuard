from __future__ import annotations

"""Run the canonical Phase 0 baseline matrix."""

import argparse
from pathlib import Path

from phase0.baselines import run_phase0_baselines


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the canonical Phase 0 baseline matrix.")
    parser.add_argument("--output-root", default="outputs/baseline", help="Directory for Phase 0 artifacts.")
    parser.add_argument("--agents", nargs="*", default=None, help="Optional agent filter, e.g. react sec_react.")
    parser.add_argument("--benchmarks", nargs="*", default=None, help="Optional benchmark filter, e.g. agentharm asb.")
    parser.add_argument("--task-nums", default=1, type=int, help="Number of ASB tasks to keep per agent.")
    parser.add_argument("--skip-readiness", action="store_true", help="Skip the readiness gate before running baselines.")
    args = parser.parse_args()

    manifest = run_phase0_baselines(
        output_root=Path(args.output_root),
        agents=args.agents,
        benchmarks=args.benchmarks,
        task_nums=args.task_nums,
        skip_readiness=args.skip_readiness,
    )

    print(f"Phase 0 run manifest: {Path(args.output_root) / 'run_manifest.json'}")
    exit_code = 0
    for run in manifest["runs"]:
        print(f"[{run['status'].upper()}] {run['benchmark']} {run['agent']} {run['scope']} -> {run['artifact_path']}")
        if run["status"] not in {"completed", "skipped_complete"}:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
