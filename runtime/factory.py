from __future__ import annotations

"""模型对象工厂。

上层 agent 文件只需要把顶部配置区的字段传进来，这里负责把配置打包成
统一的 `RuntimeModelConfig`，并创建普通模型或 guardian 模型对象。
"""

from .modeling import RuntimeModelConfig, StandaloneGuardian, StandaloneModel


def create_model_from_config(**kwargs) -> StandaloneModel:
    """根据配置创建普通 agent model。"""
    return StandaloneModel(RuntimeModelConfig(**kwargs))


def create_guard_from_config(**kwargs) -> StandaloneGuardian:
    """根据配置创建 guardian model。"""
    return StandaloneGuardian(RuntimeModelConfig(**kwargs))
