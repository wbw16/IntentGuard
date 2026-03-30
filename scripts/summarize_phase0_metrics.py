from __future__ import annotations

"""Generate `metrics_summary.json` for Phase 0 baseline artifacts."""

import argparse
from pathlib import Path

from phase0.scoring import generate_metrics_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phase 0 ASR/TCR summaries from baseline outputs.")
    parser.add_argument("--output-root", default="outputs/baseline", help="Directory containing baseline artifacts.")
    parser.add_argument("--agents", nargs="*", default=None, help="Optional agent filter, e.g. react sec_react.")
    parser.add_argument("--benchmarks", nargs="*", default=None, help="Optional benchmark filter, e.g. agentharm asb.")
    parser.add_argument("--task-nums", default=1, type=int, help="Number of ASB tasks kept per agent in the source runs.")
    args = parser.parse_args()

    summary = generate_metrics_summary(
        output_root=Path(args.output_root),
        agents=args.agents,
        benchmarks=args.benchmarks,
        task_nums=args.task_nums,
    )

    print(f"Phase 0 metrics summary: {Path(args.output_root) / 'metrics_summary.json'}")
    for entry in summary["entries"]:
        print(
            f"[{entry['status'].upper()}] {entry['benchmark']} {entry['agent']} {entry['scope']} "
            f"ASR={entry['asr']} TCR={entry['tcr']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
