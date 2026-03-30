from __future__ import annotations

"""Validate repo-root readiness for the Phase 0 baseline workflow."""

import argparse
from pathlib import Path

from phase0.readiness import collect_phase0_readiness, write_readiness_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 0 baseline prerequisites.")
    parser.add_argument("--output-root", default="outputs/baseline", help="Directory for readiness and baseline artifacts.")
    args = parser.parse_args()

    output_root = Path(args.output_root)
    report = collect_phase0_readiness(output_root=output_root)
    report_path = write_readiness_report(report, output_root=output_root)

    print(f"Phase 0 readiness report: {report_path}")
    for check in report["checks"]:
        print(f"[{check['status'].upper()}] {check['id']}: {check['summary']}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
