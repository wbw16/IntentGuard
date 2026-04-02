from __future__ import annotations

"""First-class Guard subsystem exports."""

from .config import GuardConfig, GuardConfigurationError, resolve_guard_config
from .subsystem import (
    DEFAULT_GUARD_BLOCK_THRESHOLD,
    DEFAULT_GUARD_MAX_ATTEMPTS,
    DEFAULT_GUARD_TEMPLATE_KEY,
    GuardDecision,
    GuardEvaluationRequest,
    GuardSubsystem,
)

__all__ = [
    "DEFAULT_GUARD_BLOCK_THRESHOLD",
    "DEFAULT_GUARD_MAX_ATTEMPTS",
    "DEFAULT_GUARD_TEMPLATE_KEY",
    "GuardConfig",
    "GuardConfigurationError",
    "GuardDecision",
    "GuardEvaluationRequest",
    "GuardSubsystem",
    "resolve_guard_config",
]
