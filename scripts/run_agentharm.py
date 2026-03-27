from __future__ import annotations

"""AgentHarm 的命令行入口。"""

import argparse
from pathlib import Path

from standalone_agent_env.agents import get_agent_builder
from standalone_agent_env.processors.agentharm import AgentHarmProcessor


def main():
    """解析命令行参数并启动 AgentHarm 实验。"""
    parser = argparse.ArgumentParser(description="Run AgentHarm with a standalone agent strategy.")
    parser.add_argument("--agent", default="react", help="Agent strategy name.")
    parser.add_argument("--subset", default="harmful", choices=["harmful", "benign", "attack"])
    parser.add_argument("--output", default="", help="Output directory. Defaults under standalone_agent_env/outputs.")
    args = parser.parse_args()

    # 先按策略名创建对应 agent，再交给处理器加载本地数据运行。
    builder = get_agent_builder(args.agent)
    agent = builder()
    output_dir = Path(args.output) if args.output else Path("standalone_agent_env/outputs/agentharm") / args.agent / args.subset

    processor = AgentHarmProcessor(agent=agent, output_save_dir=output_dir, subtask=args.subset)
    if args.subset == "attack":
        processor.run_attack()
    else:
        processor.run()


if __name__ == "__main__":
    main()
