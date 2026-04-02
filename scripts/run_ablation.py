from __future__ import annotations

"""消融实验入口。

用法：
    python -m scripts.run_ablation
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase0.common import load_repo_env


def main():
    load_repo_env()

    from evaluation.ablation import AblationRunner
    from evaluation.report_generator import ReportGenerator

    runner = AblationRunner()
    results = runner.run_all()

    reporter = ReportGenerator(output_dir="outputs/final")
    reporter.generate_full_report([], ablation_results=results)

    print("\nDone!")


if __name__ == "__main__":
    main()
