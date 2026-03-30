from __future__ import annotations

"""Phase 0 baseline orchestration helpers."""

from pathlib import Path
from typing import Any, Iterable

from .common import (
    BaselineRunSpec,
    DEFAULT_BASELINE_ROOT,
    build_phase0_run_specs,
    count_meta_records,
    expected_samples_for_spec,
    load_repo_env,
    now_iso,
    read_json,
    relative_to_repo,
    write_json,
)
from .readiness import collect_phase0_readiness, write_readiness_report


def _manifest_path(output_root: Path) -> Path:
    return output_root / "run_manifest.json"


def _load_manifest(output_root: Path) -> dict[str, Any]:
    path = _manifest_path(output_root)
    if not path.exists():
        return {"generated_at": now_iso(), "runs": []}
    return read_json(path)


def _save_manifest(output_root: Path, manifest: dict[str, Any]) -> Path:
    path = _manifest_path(output_root)
    write_json(path, manifest)
    return path


def _run_key(spec: BaselineRunSpec) -> tuple[str, str, str]:
    return spec.benchmark, spec.agent, spec.scope


def _execute_baseline_run(spec: BaselineRunSpec, output_root: Path) -> dict[str, Any]:
    load_repo_env()

    meta_path = spec.artifact_path(output_root=output_root)
    output_dir = meta_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    expected_samples = expected_samples_for_spec(spec)
    actual_before = count_meta_records(meta_path)
    result: dict[str, Any] = {
        "benchmark": spec.benchmark,
        "agent": spec.agent,
        "scope": spec.scope,
        "task_nums": spec.task_nums,
        "expected_samples": expected_samples,
        "actual_samples_before": actual_before,
        "actual_samples_after": actual_before,
        "status": "pending",
        "resumed": bool(actual_before),
        "artifact_path": relative_to_repo(meta_path),
        "output_dir": relative_to_repo(output_dir),
    }

    if actual_before is None:
        result["status"] = "invalid_existing_artifact"
        result["error"] = "Existing meta_data.json is not valid JSON."
        return result

    if expected_samples > 0 and actual_before >= expected_samples:
        result["status"] = "skipped_complete"
        return result

    try:
        from agents import get_agent_builder

        agent = get_agent_builder(spec.agent)()
        if spec.benchmark == "agentharm":
            from processors.agentharm import AgentHarmProcessor

            processor = AgentHarmProcessor(agent=agent, output_save_dir=output_dir, subtask=spec.scope)
            processor.run()
        elif spec.benchmark == "asb":
            from processors.asb import ASBProcessor

            processor = ASBProcessor(agent=agent, output_save_dir=output_dir, attack_type=spec.scope.upper())
            processor.run(task_nums=spec.task_nums)
        else:
            raise ValueError(f"Unsupported benchmark: {spec.benchmark}")
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        actual_after = count_meta_records(meta_path)
        result["actual_samples_after"] = actual_after
        return result

    actual_after = count_meta_records(meta_path)
    result["actual_samples_after"] = actual_after
    if actual_after is None:
        result["status"] = "invalid_output"
        result["error"] = "Generated meta_data.json is not valid JSON."
    elif expected_samples > 0 and actual_after >= expected_samples:
        result["status"] = "completed"
    elif actual_after and actual_after > (actual_before or 0):
        result["status"] = "partial"
    else:
        result["status"] = "failed"
        result["error"] = "Run finished without producing additional records."
    return result


def run_phase0_baselines(
    output_root: Path | None = None,
    agents: Iterable[str] | None = None,
    benchmarks: Iterable[str] | None = None,
    task_nums: int = 1,
    skip_readiness: bool = False,
) -> dict[str, Any]:
    """Execute the Phase 0 baseline matrix and persist the run manifest."""

    resolved_output_root = (output_root or DEFAULT_BASELINE_ROOT).resolve()
    resolved_output_root.mkdir(parents=True, exist_ok=True)

    readiness_report = None
    if not skip_readiness:
        readiness_report = collect_phase0_readiness(output_root=resolved_output_root)
        write_readiness_report(readiness_report, output_root=resolved_output_root)
        if not readiness_report["ok"]:
            raise RuntimeError("Phase 0 readiness checks failed. See outputs/baseline/readiness/report.json for details.")

    existing_manifest = _load_manifest(resolved_output_root)
    existing_runs = {
        (row["benchmark"], row["agent"], row["scope"]): row
        for row in existing_manifest.get("runs", [])
        if all(key in row for key in ("benchmark", "agent", "scope"))
    }

    runs: list[dict[str, Any]] = []
    for spec in build_phase0_run_specs(agents=agents, benchmarks=benchmarks, task_nums=task_nums):
        run = _execute_baseline_run(spec, output_root=resolved_output_root)
        previous = existing_runs.get(_run_key(spec))
        if previous and run["status"] == "skipped_complete":
            merged = dict(previous)
            merged.update(run)
            run = merged
        runs.append(run)

    manifest = {
        "generated_at": now_iso(),
        "output_root": relative_to_repo(resolved_output_root),
        "readiness_report": relative_to_repo(resolved_output_root / "readiness" / "report.json"),
        "task_nums": task_nums,
        "skip_readiness": skip_readiness,
        "runs": runs,
    }
    _save_manifest(resolved_output_root, manifest)
    if readiness_report is not None:
        manifest["readiness_ok"] = readiness_report["ok"]
    return manifest
