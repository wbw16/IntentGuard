"""攻击数据采集器：从各数据集读取样本并归一化为 AttackScenario。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from training.label_schema import (
    AttackScenario,
    AttackType,
    _load_training_config,
)

BASE_DIR = Path(__file__).resolve().parents[1]


class DataCollector:
    """从 agentharm / asb / agentdojo 采集攻击与正常场景。"""

    def __init__(self) -> None:
        self._cfg = _load_training_config().get("data_sources", {})

    # ------------------------------------------------------------------
    # AgentHarm
    # ------------------------------------------------------------------

    def collect_agentharm(self, subset: str = "harmful") -> list[AttackScenario]:
        """从 AgentHarm 数据集采集场景。"""
        cfg = self._cfg.get("agentharm", {})
        data_path = BASE_DIR / cfg.get(subset, f"data/agentharm/dataset/{subset}_behaviors_test_public.json")
        if not data_path.exists():
            return []

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        scenarios: list[AttackScenario] = []
        for item in data.get("behaviors", []):
            attack_type = AttackType.HARMFUL if subset == "harmful" else AttackType.NONE
            harmful_tools = item.get("harmful_tool", [])
            scenarios.append(AttackScenario(
                scenario_id=f"agentharm_{subset}_{item.get('id', '')}",
                source="agentharm",
                query=item.get("prompt", ""),
                tools=item.get("target_functions", []),
                attack_type=attack_type,
                expected_harmful_tool=harmful_tools[0] if harmful_tools else "",
                metadata={
                    "name": item.get("name", ""),
                    "category": item.get("category", ""),
                    "grading_function": item.get("grading_function", ""),
                },
            ))
        return scenarios

    # ------------------------------------------------------------------
    # ASB
    # ------------------------------------------------------------------

    def collect_asb(self, attack_type: str = "OPI") -> list[AttackScenario]:
        """从 ASB 数据集采集攻击场景。"""
        cfg = self._cfg.get("asb", {})
        tasks_path = BASE_DIR / cfg.get("tasks", "data/asb/data/agent_task.jsonl")
        attack_path = BASE_DIR / cfg.get("attack_tools", "data/asb/data/all_attack_tools.jsonl")
        normal_path = BASE_DIR / cfg.get("normal_tools", "data/asb/data/all_normal_tools.jsonl")

        tasks = _read_jsonl(tasks_path)
        attacks = _read_jsonl(attack_path)
        normals = _read_jsonl(normal_path)

        # 按 agent 分组
        normal_by_agent: dict[str, list[dict]] = {}
        for t in normals:
            agent = t.get("Corresponding Agent", "")
            normal_by_agent.setdefault(agent, []).append(t)

        at = AttackType.OPI if attack_type == "OPI" else AttackType.DPI
        scenarios: list[AttackScenario] = []
        idx = 0

        for task_group in tasks:
            agent_name = task_group.get("agent_name", "")
            agent_attacks = [a for a in attacks if a.get("Corresponding Agent") == agent_name]
            agent_normals = normal_by_agent.get(agent_name, [])
            all_tools = [t.get("Tool Name", "") for t in agent_normals]

            for task_query in task_group.get("tasks", []):
                for atk in agent_attacks:
                    tool_descs = {t.get("Tool Name", ""): t.get("Description", "") for t in agent_normals}
                    tool_descs[atk["Attacker Tool"]] = atk.get("Description", "")
                    scenarios.append(AttackScenario(
                        scenario_id=f"asb_{attack_type}_{idx}",
                        source="asb",
                        query=task_query,
                        tools=all_tools + [atk["Attacker Tool"]],
                        tool_descriptions=tool_descs,
                        attack_type=at,
                        attack_instruction=atk.get("Attacker Instruction", ""),
                        expected_harmful_tool=atk.get("Attacker Tool", ""),
                        metadata={
                            "agent_name": agent_name,
                            "attack_goal": atk.get("Attack goal", ""),
                            "aggressive": atk.get("Aggressive", ""),
                        },
                    ))
                    idx += 1

        return scenarios

    # ------------------------------------------------------------------
    # AgentDojo
    # ------------------------------------------------------------------

    def collect_agentdojo(self) -> list[AttackScenario]:
        """从 AgentDojo 数据集采集注入场景。"""
        cfg = self._cfg.get("agentdojo", {})
        suites_dir = BASE_DIR / cfg.get("suites_dir", "data/agentdojo/suites")
        suites = cfg.get("suites", ["banking", "slack", "travel", "workspace"])

        scenarios: list[AttackScenario] = []
        idx = 0

        for suite in suites:
            suite_dir = suites_dir / suite
            env_file = suite_dir / "environment.yaml"
            inj_file = suite_dir / "injection_vectors.yaml"
            if not env_file.exists():
                continue

            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    env_data = yaml.safe_load(f) or {}
            except yaml.YAMLError:
                env_data = {}

            injections: dict = {}
            if inj_file.exists():
                try:
                    with open(inj_file, "r", encoding="utf-8") as f:
                        injections = yaml.safe_load(f) or {}
                except yaml.YAMLError:
                    injections = {}

            tools = list(env_data.get("tools", {}).keys()) if isinstance(env_data.get("tools"), dict) else []

            for inj_name, inj_data in injections.items():
                scenarios.append(AttackScenario(
                    scenario_id=f"agentdojo_{suite}_{idx}",
                    source="agentdojo",
                    query=str(inj_data.get("task", "")),
                    tools=tools,
                    attack_type=AttackType.INJECTION,
                    attack_instruction=str(inj_data.get("injection", "")),
                    metadata={"suite": suite, "injection_name": inj_name},
                ))
                idx += 1

        return scenarios

    # ------------------------------------------------------------------
    # 统一采集
    # ------------------------------------------------------------------

    def collect_all(self) -> list[AttackScenario]:
        """采集所有数据源的场景。"""
        scenarios: list[AttackScenario] = []
        scenarios.extend(self.collect_agentharm("harmful"))
        scenarios.extend(self.collect_agentharm("benign"))
        scenarios.extend(self.collect_asb("OPI"))
        scenarios.extend(self.collect_asb("DPI"))
        scenarios.extend(self.collect_agentdojo())
        return scenarios


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

import yaml  # noqa: E402 — deferred to avoid circular import at module level


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    items: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items
