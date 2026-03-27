from __future__ import annotations

"""独立实验环境的 agent 注册表。

这里维护“策略名 -> builder 函数”的懒加载映射，
避免导入一个 agent 时连带触发所有可选依赖。
"""

import importlib


AGENT_BUILDERS = {
    # 每个条目都指向一个 `build_agent` 工厂函数。
    "default": ("standalone_agent_env.agents.default_agent", "build_agent"),
    "react": ("standalone_agent_env.agents.react_agent", "build_agent"),
    "sec_react": ("standalone_agent_env.agents.sec_react_agent", "build_agent"),
    "planexecute": ("standalone_agent_env.agents.planexecute_agent", "build_agent"),
    "sec_planexecute": ("standalone_agent_env.agents.sec_planexecute_agent", "build_agent"),
    "ipiguard": ("standalone_agent_env.agents.ipiguard_agent", "build_agent"),
    "react_firewall": ("standalone_agent_env.agents.react_firewall_agent", "build_agent"),
}


def get_agent_builder(agent_name: str):
    """按策略名返回对应的 builder 函数。"""
    if agent_name not in AGENT_BUILDERS:
        supported = ", ".join(sorted(AGENT_BUILDERS))
        raise ValueError(f"Unsupported agent '{agent_name}'. Supported agents: {supported}")

    module_name, attr_name = AGENT_BUILDERS[agent_name]
    # 懒加载可以避免像 `ipiguard` 这种带可选依赖的策略在导入时影响其它策略。
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)
