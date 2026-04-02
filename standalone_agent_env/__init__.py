"""Compatibility namespace for the extracted standalone agent environment."""

from __future__ import annotations

import importlib
import sys


def _alias_package(alias: str, target: str) -> None:
    module = importlib.import_module(target)
    sys.modules[f"{__name__}.{alias}"] = module
    setattr(sys.modules[__name__], alias, module)


for alias_name, target_name in (
    ("runtime", "runtime"),
    ("processors", "processors"),
    ("agents", "agents"),
    ("guard", "guard"),
):
    _alias_package(alias_name, target_name)

__all__ = ["agents", "guard", "processors", "runtime"]
