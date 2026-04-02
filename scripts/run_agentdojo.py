from __future__ import annotations

"""AgentDojo 的命令行入口。"""

import argparse
from pathlib import Path

from phase0.common import load_repo_env


def main():
    """解析命令行参数并启动 AgentDojo 实验。"""
    load_repo_env()

    from agents import get_agent_builder
    from processors.agentdojo import AgentDojoProcessor

    parser = argparse.ArgumentParser(description="Run AgentDojo with a standalone agent strategy.")
    parser.add_argument("--agent", default="react", help="Agent strategy name.")
    parser.add_argument("--suite", default="banking", choices=["banking", "slack", "travel", "workspace", "all"])
    parser.add_argument("--attack-mode", default="injection", choices=["injection", "benign"])
    parser.add_argument("--output", default="", help="Output directory.")
    args = parser.parse_args()

    builder = get_agent_builder(args.agent)
    agent = builder()

    suites = ["banking", "slack", "travel", "workspace"] if args.suite == "all" else [args.suite]

    for suite in suites:
        print(f"\n{'='*60}")
        print(f"Suite: {suite} | Mode: {args.attack_mode} | Agent: {args.agent}")
        print(f"{'='*60}")

        output_dir = (
            Path(args.output) / suite if args.output
            else Path("outputs/agentdojo") / args.agent / suite / args.attack_mode
        )
        processor = AgentDojoProcessor(
            agent=agent,
            output_save_dir=output_dir,
            suite=suite,
            attack_mode=args.attack_mode,
        )
        results = processor.run()
        print(f"  Completed: {len(results)} tasks")


if __name__ == "__main__":
    main()
