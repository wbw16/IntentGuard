from __future__ import annotations

"""IntentGuard 全量评测入口。

用法：
    python -m scripts.run_intentguard_eval [--agents AGENT ...] [--benchmarks BENCH ...]
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase0.common import load_repo_env


def main():
    load_repo_env()

    from evaluation.eval_runner import EvalRunner
    from evaluation.report_generator import ReportGenerator

    parser = argparse.ArgumentParser(description="IntentGuard 全量评测")
    parser.add_argument("--agents", nargs="+", default=None,
                        help="要评测的 agent 列表 (默认: 全部)")
    parser.add_argument("--benchmarks", nargs="+", default=None,
                        help="要评测的 benchmark 列表 (默认: 全部)")
    parser.add_argument("--report-dir", default="outputs/final",
                        help="报告输出目录")
    args = parser.parse_args()

    runner = EvalRunner()
    results = runner.run_all(agents=args.agents, benchmarks=args.benchmarks)

    reporter = ReportGenerator(output_dir=args.report_dir)
    reporter.generate_full_report(results)

    print("\nDone!")


if __name__ == "__main__":
    main()
