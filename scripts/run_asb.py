from __future__ import annotations

"""ASB 的命令行入口。"""

import argparse
from pathlib import Path

from phase0.common import load_repo_env


def main():
    """解析命令行参数并启动 ASB 实验。"""
    load_repo_env()

    from agents import get_agent_builder
    from processors.asb import ASBProcessor

    parser = argparse.ArgumentParser(description="Run ASB with a standalone agent strategy.")
    parser.add_argument("--agent", default="sec_react", help="Agent strategy name.")
    parser.add_argument("--attack-type", default="OPI", choices=["OPI", "DPI"])
    parser.add_argument("--task-nums", default=1, type=int, help="Number of tasks to keep per ASB agent.")
    parser.add_argument("--output", default="", help="Output directory. Defaults to outputs/agentdojo/<agent>/<attack_type>.")
    args = parser.parse_args()

    # 按选择的策略和攻击类型构造实验运行对象。
    builder = get_agent_builder(args.agent)
    agent = builder()
    output_dir = Path(args.output) if args.output else Path("outputs/agentdojo") / args.agent / args.attack_type

    processor = ASBProcessor(agent=agent, output_save_dir=output_dir, attack_type=args.attack_type)
    processor.run(task_nums=args.task_nums)


if __name__ == "__main__":
    main()
