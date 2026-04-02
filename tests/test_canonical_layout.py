from __future__ import annotations

"""Regression tests for canonical layout, compatibility aliases, and path assumptions."""

import importlib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CANONICAL_CODE_MODULES = [
    "agents",
    "runtime",
    "runtime.core",
    "runtime.factory",
    "runtime.modeling",
    "runtime.parsers",
    "runtime.prompts",
    "runtime.function_call",
    "guard",
    "processors",
    "processors.agentharm",
    "processors.asb",
    "phase0",
    "phase0.common",
    "phase0.readiness",
    "phase0.scoring",
    "phase0.baselines",
    "guardrail",
    "training",
    "evaluation",
]

CANONICAL_DIRS = [
    "agents",
    "runtime",
    "guard",
    "guardrail",
    "training",
    "evaluation",
    "processors",
    "phase0",
    "scripts",
    "tests",
    "configs",
    "data",
    "data/agentharm",
    "data/asb",
    "data/agentdojo",
    "data/manifests",
    "data/guard_training",
    "outputs",
    "outputs/baseline",
    "outputs/agentdojo",
    "outputs/guard_models",
    "outputs/ablation",
    "outputs/final",
]

COMPATIBILITY_ALIASES = [
    ("standalone_agent_env.runtime", "runtime"),
    ("standalone_agent_env.agents", "agents"),
    ("standalone_agent_env.processors", "processors"),
    ("standalone_agent_env.guard", "guard"),
]


class CanonicalImportTests(unittest.TestCase):
    def test_canonical_modules_are_importable(self) -> None:
        for module_name in CANONICAL_CODE_MODULES:
            with self.subTest(module=module_name):
                try:
                    importlib.import_module(module_name)
                except ImportError as exc:
                    self.fail(f"Canonical module '{module_name}' could not be imported: {exc}")

    def test_agents_registry_uses_canonical_paths(self) -> None:
        from agents import AGENT_BUILDERS

        for name, (module_path, _) in AGENT_BUILDERS.items():
            with self.subTest(agent=name):
                self.assertFalse(
                    module_path.startswith("standalone_agent_env."),
                    f"Agent '{name}' registry entry still uses compatibility path: {module_path}",
                )
                self.assertTrue(
                    module_path.startswith("agents."),
                    f"Agent '{name}' registry entry does not use canonical 'agents.*' path: {module_path}",
                )

    def test_phase0_required_imports_are_canonical(self) -> None:
        from phase0.common import REQUIRED_RUNTIME_IMPORTS

        for module_name in REQUIRED_RUNTIME_IMPORTS:
            with self.subTest(module=module_name):
                self.assertFalse(
                    module_name.startswith("standalone_agent_env."),
                    f"REQUIRED_RUNTIME_IMPORTS contains non-canonical path: {module_name}",
                )


class CompatibilityAliasTests(unittest.TestCase):
    def test_standalone_namespace_aliases_resolve_to_canonical_modules(self) -> None:
        for compat_path, canonical_path in COMPATIBILITY_ALIASES:
            with self.subTest(compat=compat_path, canonical=canonical_path):
                compat_module = importlib.import_module(compat_path)
                canonical_module = importlib.import_module(canonical_path)
                self.assertIs(
                    compat_module,
                    canonical_module,
                    f"Compatibility alias '{compat_path}' does not resolve to the same object as '{canonical_path}'",
                )

    def test_standalone_namespace_script_shims_import_from_canonical_scripts(self) -> None:
        script_names = [
            "run_agentharm",
            "run_asb",
            "run_phase0_baselines",
            "summarize_phase0_metrics",
            "check_phase0_env",
        ]
        for name in script_names:
            with self.subTest(script=name):
                compat_mod = importlib.import_module(f"standalone_agent_env.scripts.{name}")
                canonical_mod = importlib.import_module(f"scripts.{name}")
                compat_main = getattr(compat_mod, "main", None)
                canonical_main = getattr(canonical_mod, "main", None)
                self.assertIsNotNone(canonical_main, f"scripts.{name} has no 'main' attribute")
                self.assertIs(
                    compat_main,
                    canonical_main,
                    f"Compatibility shim standalone_agent_env.scripts.{name} does not forward to canonical scripts.{name}.main",
                )


class CanonicalDirectoryTests(unittest.TestCase):
    def test_canonical_directories_exist(self) -> None:
        for rel_path in CANONICAL_DIRS:
            with self.subTest(path=rel_path):
                full_path = REPO_ROOT / rel_path
                self.assertTrue(
                    full_path.is_dir(),
                    f"Canonical directory '{rel_path}' does not exist at {full_path}",
                )

    def test_structure_map_exists(self) -> None:
        self.assertTrue(
            (REPO_ROOT / "STRUCTURE.md").is_file(),
            "STRUCTURE.md is missing from the repository root",
        )

    def test_outputs_not_nested_under_data(self) -> None:
        outputs_under_data = list((REPO_ROOT / "data").glob("**/outputs"))
        self.assertEqual(
            outputs_under_data,
            [],
            f"Generated outputs found under data/: {outputs_under_data}",
        )
