from __future__ import annotations

"""Readiness checks for Phase 0 baseline execution."""

import importlib
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .common import (
    AGENT_ENV_PREFIXES,
    DEFAULT_BASELINE_ROOT,
    DEFAULT_ENV_FILE,
    PHASE0_AGENTS,
    REQUIRED_DATASET_PATHS,
    REQUIRED_RUNTIME_IMPORTS,
    is_placeholder,
    load_repo_env,
    now_iso,
    relative_to_repo,
    resolve_agent_env_config,
    write_json,
)


def _check_runtime_imports() -> dict[str, Any]:
    failed: list[dict[str, str]] = []
    for module_name in REQUIRED_RUNTIME_IMPORTS:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            failed.append({"module": module_name, "error": f"{type(exc).__name__}: {exc}"})

    if failed:
        return {
            "id": "runtime_imports",
            "status": "fail",
            "summary": "One or more required runtime imports failed.",
            "details": failed,
            "remediation": "Verify the canonical runtime and processor modules are importable.",
        }

    return {
        "id": "runtime_imports",
        "status": "pass",
        "summary": "Required runtime imports resolved successfully.",
        "details": list(REQUIRED_RUNTIME_IMPORTS),
    }


def _check_required_agents() -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    try:
        from agents import get_agent_builder
    except Exception as exc:
        return {
            "id": "baseline_agents",
            "status": "fail",
            "summary": "The baseline agent registry could not be imported.",
            "details": [{"error": f"{type(exc).__name__}: {exc}"}],
            "remediation": "Fix the agents module before running Phase 0 baselines.",
        }

    for agent_name in PHASE0_AGENTS:
        try:
            get_agent_builder(agent_name)
        except Exception as exc:
            failures.append({"agent": agent_name, "error": f"{type(exc).__name__}: {exc}"})

    if failures:
        return {
            "id": "baseline_agents",
            "status": "fail",
            "summary": "One or more required Phase 0 agents could not be resolved.",
            "details": failures,
            "remediation": "Confirm that the `react` and `sec_react` agent modules import cleanly.",
        }

    return {
        "id": "baseline_agents",
        "status": "pass",
        "summary": "Required Phase 0 agent builders are available.",
        "details": list(PHASE0_AGENTS),
    }


def _check_datasets() -> dict[str, Any]:
    missing = [
        {"name": dataset_name, "path": relative_to_repo(path)}
        for dataset_name, path in REQUIRED_DATASET_PATHS.items()
        if not path.exists()
    ]
    if missing:
        return {
            "id": "datasets",
            "status": "fail",
            "summary": "One or more required benchmark datasets are missing.",
            "details": missing,
            "remediation": "Restore the missing local benchmark data before running baseline experiments.",
        }

    return {
        "id": "datasets",
        "status": "pass",
        "summary": "All required benchmark datasets are present.",
        "details": {name: relative_to_repo(path) for name, path in REQUIRED_DATASET_PATHS.items()},
    }


def _check_output_root(output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    readiness_dir = output_root / "readiness"
    readiness_dir.mkdir(parents=True, exist_ok=True)

    try:
        with NamedTemporaryFile("w", encoding="utf-8", dir=readiness_dir, delete=True) as handle:
            handle.write("phase0 readiness check\n")
            handle.flush()
    except OSError as exc:
        return {
            "id": "output_root",
            "status": "fail",
            "summary": "The baseline output root is not writable.",
            "details": [{"path": relative_to_repo(output_root), "error": f"{type(exc).__name__}: {exc}"}],
            "remediation": "Choose a writable output directory for Phase 0 artifacts.",
        }

    return {
        "id": "output_root",
        "status": "pass",
        "summary": "The baseline output root is writable.",
        "details": {"path": relative_to_repo(output_root)},
    }


def _check_model_config() -> dict[str, Any]:
    problems: list[dict[str, Any]] = []
    for agent_name in PHASE0_AGENTS:
        config = resolve_agent_env_config(agent_name)
        missing_fields: list[str] = []
        remediation: list[str] = []

        if is_placeholder(config["model_name"]):
            missing_fields.append("model_name")
            remediation.append(f"Set {AGENT_ENV_PREFIXES[agent_name]}_MODEL_NAME in the environment or .env.")

        model_type = config["model_type"] or "api"
        if model_type == "api":
            if is_placeholder(config["api_key"]):
                missing_fields.append("api_key")
                remediation.append(f"Set {AGENT_ENV_PREFIXES[agent_name]}_API_KEY with a real credential.")
            if is_placeholder(config["api_base"]):
                missing_fields.append("api_base")
                remediation.append(f"Set {AGENT_ENV_PREFIXES[agent_name]}_API_BASE to a reachable API endpoint.")
        elif is_placeholder(config["model_path"]):
            missing_fields.append("model_path")
            remediation.append(f"Set {AGENT_ENV_PREFIXES[agent_name]}_MODEL_PATH for local model execution.")

        if missing_fields:
            problems.append(
                {
                    "agent": agent_name,
                    "model_type": model_type,
                    "missing_fields": missing_fields,
                    "remediation": remediation,
                }
            )

    if problems:
        return {
            "id": "model_config",
            "status": "fail",
            "summary": "One or more required model settings are unset or still use placeholder values.",
            "details": problems,
            "remediation": "Populate the required `STANDALONE_*` model settings before launching Phase 0 baselines.",
        }

    return {
        "id": "model_config",
        "status": "pass",
        "summary": "Required Phase 0 model settings are configured.",
        "details": list(PHASE0_AGENTS),
    }


def collect_phase0_readiness(
    output_root: Path | None = None,
    env_file: Path | None = None,
) -> dict[str, Any]:
    """Collect a machine-readable Phase 0 readiness report."""

    env_path = env_file or DEFAULT_ENV_FILE
    load_repo_env(env_path)
    resolved_output_root = (output_root or DEFAULT_BASELINE_ROOT).resolve()

    checks = [
        _check_runtime_imports(),
        _check_required_agents(),
        _check_datasets(),
        _check_output_root(resolved_output_root),
        _check_model_config(),
    ]
    passed = sum(check["status"] == "pass" for check in checks)
    failed = sum(check["status"] == "fail" for check in checks)

    return {
        "generated_at": now_iso(),
        "ok": failed == 0,
        "env_file": relative_to_repo(env_path),
        "output_root": relative_to_repo(resolved_output_root),
        "summary": {
            "total_checks": len(checks),
            "passed": passed,
            "failed": failed,
        },
        "checks": checks,
    }


def write_readiness_report(report: dict[str, Any], output_root: Path | None = None) -> Path:
    """Persist a readiness report under the canonical baseline location."""

    resolved_output_root = (output_root or DEFAULT_BASELINE_ROOT).resolve()
    report_path = resolved_output_root / "readiness" / "report.json"
    write_json(report_path, report)
    return report_path
