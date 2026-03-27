from __future__ import annotations

"""工作流型 agent 使用的工具调用结构体。"""

from dataclasses import dataclass, field


@dataclass
class FunctionCall:
    """表示一次结构化工具调用。

    Attributes:
        function: 工具名。
        args: 该工具调用对应的参数字典。
        id: 在 DAG 或执行链里的节点标识。
    """

    function: str
    args: dict = field(default_factory=dict)
    id: str = ""
