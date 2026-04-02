from __future__ import annotations

"""Shared Guard configuration resolution."""

from dataclasses import dataclass
import os
from typing import TYPE_CHECKING, Mapping

from .subsystem import (
    DEFAULT_GUARD_BLOCK_THRESHOLD,
    DEFAULT_GUARD_MAX_ATTEMPTS,
    DEFAULT_GUARD_TEMPLATE_KEY,
)

if TYPE_CHECKING:
    from runtime.modeling import RuntimeModelConfig


class GuardConfigurationError(ValueError):
    """Raised when a Guard configuration cannot be resolved."""


@dataclass(frozen=True)
class GuardConfig:
    """Configuration owned by the Guard subsystem."""

    model_config: "RuntimeModelConfig"
    block_threshold: float = DEFAULT_GUARD_BLOCK_THRESHOLD
    max_attempts: int = DEFAULT_GUARD_MAX_ATTEMPTS
    default_template_key: str = DEFAULT_GUARD_TEMPLATE_KEY

    @classmethod
    def from_model_config(
        cls,
        model_config: "RuntimeModelConfig",
        *,
        block_threshold: float = DEFAULT_GUARD_BLOCK_THRESHOLD,
        max_attempts: int = DEFAULT_GUARD_MAX_ATTEMPTS,
        default_template_key: str = DEFAULT_GUARD_TEMPLATE_KEY,
    ) -> "GuardConfig":
        return cls(
            model_config=model_config,
            block_threshold=block_threshold,
            max_attempts=max_attempts,
            default_template_key=default_template_key,
        )


def resolve_guard_config(
    agent_prefix: str,
    primary_config: "RuntimeModelConfig",
    *,
    environ: Mapping[str, str] | None = None,
) -> GuardConfig:
    """Resolve Guard settings while preserving existing per-agent env names."""

    if not agent_prefix:
        raise GuardConfigurationError("agent_prefix is required to resolve guard configuration")

    if primary_config is None:
        raise GuardConfigurationError("primary_config is required to resolve guard configuration")

    env = os.environ if environ is None else environ

    from runtime.modeling import RuntimeModelConfig

    def _env(key: str, fallback: str) -> str:
        return env.get(f"{agent_prefix}_{key}", fallback)

    model_config = RuntimeModelConfig(
        model_name=_env("GUARD_MODEL_NAME", primary_config.model_name),
        model_type=_env("GUARD_MODEL_TYPE", primary_config.model_type),
        model_path=_env("GUARD_MODEL_PATH", primary_config.model_path),
        api_base=_env("GUARD_API_BASE", primary_config.api_base),
        api_key=_env("GUARD_API_KEY", primary_config.api_key),
        temperature=float(_env("GUARD_TEMPERATURE", str(primary_config.temperature))),
        top_p=float(_env("GUARD_TOP_P", str(primary_config.top_p))),
        max_tokens=int(_env("GUARD_MAX_TOKENS", str(primary_config.max_tokens))),
        timeout=float(_env("GUARD_TIMEOUT", str(primary_config.timeout))),
    )

    return GuardConfig(
        model_config=model_config,
        block_threshold=float(_env("GUARD_BLOCK_THRESHOLD", str(DEFAULT_GUARD_BLOCK_THRESHOLD))),
        max_attempts=int(_env("GUARD_MAX_ATTEMPTS", str(DEFAULT_GUARD_MAX_ATTEMPTS))),
        default_template_key=_env("GUARD_TEMPLATE_KEY", DEFAULT_GUARD_TEMPLATE_KEY),
    )
