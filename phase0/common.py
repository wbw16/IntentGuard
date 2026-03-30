from __future__ import annotations

"""Shared helpers for Phase 0 baseline workflows."""

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE_ROOT = REPO_ROOT / "outputs" / "baseline"
DEFAULT_ENV_FILE = REPO_ROOT / ".env"
PLACEHOLDER_VALUES = {"", "REPLACE_ME", "YOUR_API_KEY"}
PHASE0_AGENTS = ("react", "sec_react")
PHASE0_BENCHMARKS = ("agentharm", "asb")
REQUIRED_RUNTIME_IMPORTS = (
    "standalone_agent_env.runtime.core",
    "standalone_agent_env.runtime.parsers",
    "standalone_agent_env.processors.agentharm",
    "standalone_agent_env.processors.asb",
)
REQUIRED_DATASET_PATHS = {
    "agentharm_harmful_dataset": REPO_ROOT / "data" / "agentharm" / "dataset" / "harmful_behaviors_test_public.json",
    "asb_tasks": REPO_ROOT / "data" / "asb" / "data" / "agent_task.jsonl",
    "asb_normal_tools": REPO_ROOT / "data" / "asb" / "data" / "all_normal_tools.jsonl",
    "asb_attack_tools": REPO_ROOT / "data" / "asb" / "data" / "all_attack_tools.jsonl",
}
AGENT_ENV_PREFIXES = {
    "react": "STANDALONE_REACT",
    "sec_react": "STANDALONE_SEC_REACT",
}
ENV_REF_PATTERN = re.compile(r"\$\{([A-Za-z0-9_]+)\}")


@dataclass(frozen=True)
class BaselineRunSpec:
    """A single Phase 0 baseline run definition."""

    benchmark: str
    agent: str
    scope: str
    task_nums: int = 1

    def output_dir(self, output_root: Path | None = None) -> Path:
        root = output_root or DEFAULT_BASELINE_ROOT
        return root / self.benchmark / self.agent / self.scope

    def artifact_path(self, output_root: Path | None = None) -> Path:
        return self.output_dir(output_root=output_root) / "meta_data.json"


def now_iso() -> str:
    """Return a UTC timestamp in ISO-8601 format."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def relative_to_repo(path: Path) -> str:
    """Return a repo-relative path when possible."""

    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def parse_dotenv(env_file: Path) -> dict[str, str]:
    """Parse a minimal dotenv file without extra dependencies."""

    if not env_file.exists():
        return {}

    raw_values: dict[str, str] = {}
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        raw_values[key] = value
    values: dict[str, str] = {}
    for key, value in raw_values.items():
        values[key] = _expand_env_refs(value, {**os.environ, **raw_values, **values})
    return values


def _expand_env_refs(value: str, scope: dict[str, str]) -> str:
    """Expand `${VAR}` references using the provided scope."""

    def _replace(match: re.Match[str]) -> str:
        return scope.get(match.group(1), "")

    previous = value
    while True:
        expanded = ENV_REF_PATTERN.sub(_replace, previous)
        if expanded == previous:
            return expanded
        previous = expanded


def load_repo_env(env_file: Path | None = None) -> dict[str, str]:
    """Load `.env` values into `os.environ` without overriding existing variables."""

    env_path = env_file or DEFAULT_ENV_FILE
    values = parse_dotenv(env_path)
    for key, value in values.items():
        os.environ.setdefault(key, value)
    return values


def read_json(path: Path) -> Any:
    """Read a JSON file."""

    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of dicts."""

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    """Write JSON with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def count_meta_records(path: Path) -> int | None:
    """Return the number of records in a saved `meta_data.json` artifact."""

    if not path.exists():
        return 0
    try:
        payload = read_json(path)
    except json.JSONDecodeError:
        return None
    return len(payload) if isinstance(payload, list) else None


def count_agentharm_behaviors(subset: str = "harmful") -> int:
    """Return the number of AgentHarm samples in the requested subset."""

    dataset_path = REPO_ROOT / "data" / "agentharm" / "dataset" / f"{subset}_behaviors_test_public.json"
    payload = read_json(dataset_path)
    return len(payload.get("behaviors", []))


def count_asb_cases(task_nums: int = 1) -> int:
    """Return the number of ASB task-attack combinations for the requested scope."""

    tasks = read_jsonl(REQUIRED_DATASET_PATHS["asb_tasks"])
    attack_tools = read_jsonl(REQUIRED_DATASET_PATHS["asb_attack_tools"])

    attack_counts: dict[str, int] = {}
    for row in attack_tools:
        agent_name = row.get("Corresponding Agent")
        if agent_name:
            attack_counts[agent_name] = attack_counts.get(agent_name, 0) + 1

    total = 0
    for row in tasks:
        task_count = len(row.get("tasks", [])[:task_nums])
        total += task_count * attack_counts.get(row.get("agent_name", ""), 0)
    return total


def expected_samples_for_spec(spec: BaselineRunSpec) -> int:
    """Return the expected sample count for a baseline run."""

    if spec.benchmark == "agentharm":
        return count_agentharm_behaviors(spec.scope)
    if spec.benchmark == "asb":
        return count_asb_cases(task_nums=spec.task_nums)
    raise ValueError(f"Unsupported benchmark: {spec.benchmark}")


def build_phase0_run_specs(
    agents: Iterable[str] | None = None,
    benchmarks: Iterable[str] | None = None,
    task_nums: int = 1,
) -> list[BaselineRunSpec]:
    """Build the default Phase 0 run matrix with optional filters."""

    selected_agents = {agent.lower() for agent in (agents or PHASE0_AGENTS)}
    selected_benchmarks = {benchmark.lower() for benchmark in (benchmarks or PHASE0_BENCHMARKS)}

    specs: list[BaselineRunSpec] = []
    for agent in PHASE0_AGENTS:
        if agent not in selected_agents:
            continue
        if "agentharm" in selected_benchmarks:
            specs.append(BaselineRunSpec(benchmark="agentharm", agent=agent, scope="harmful", task_nums=task_nums))
        if "asb" in selected_benchmarks:
            specs.append(BaselineRunSpec(benchmark="asb", agent=agent, scope="opi", task_nums=task_nums))
    return specs


def resolve_agent_env_config(agent_name: str) -> dict[str, str]:
    """Resolve the effective config for a baseline agent from the environment."""

    prefix = AGENT_ENV_PREFIXES[agent_name]
    return {
        "model_name": os.getenv(f"{prefix}_MODEL_NAME", ""),
        "model_type": os.getenv(f"{prefix}_MODEL_TYPE", "api"),
        "model_path": os.getenv(f"{prefix}_MODEL_PATH", ""),
        "api_base": os.getenv(f"{prefix}_API_BASE", ""),
        "api_key": os.getenv(f"{prefix}_API_KEY", ""),
    }


def is_placeholder(value: str | None) -> bool:
    """Return whether a string looks unset or placeholder-like."""

    return value is None or value.strip() in PLACEHOLDER_VALUES
