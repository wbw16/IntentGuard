from __future__ import annotations

"""模型对象与 Guard 子系统工厂。"""

from guard import GuardSubsystem, resolve_guard_config

from .modeling import RuntimeModelConfig, StandaloneGuardian, StandaloneModel


def create_model_from_config(config: RuntimeModelConfig | None = None, **kwargs) -> StandaloneModel:
    """根据配置创建普通 agent model。"""
    runtime_config = config or RuntimeModelConfig(**kwargs)
    return StandaloneModel(runtime_config)


def create_guard_from_config(config: RuntimeModelConfig | None = None, **kwargs) -> StandaloneGuardian:
    """根据配置创建 guardian model。"""
    runtime_config = config or RuntimeModelConfig(**kwargs)
    return StandaloneGuardian(runtime_config)


def create_guard_from_env(agent_prefix: str, primary_config: RuntimeModelConfig) -> GuardSubsystem:
    """Resolve and construct a Guard dependency through the shared env path."""
    return GuardSubsystem(resolve_guard_config(agent_prefix, primary_config))
