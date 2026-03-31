"""审计日志：将每次护栏评估记录为 JSONL。"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_DEFAULT_AUDIT_DIR = Path(__file__).parent.parent / "outputs" / "guardrail_audit"


class AuditLogger:
    """写 JSONL 审计日志到指定目录。"""

    def __init__(self, output_dir: str | None = None, *, enabled: bool = True):
        self._enabled = enabled
        self._output_dir = Path(output_dir) if output_dir else _DEFAULT_AUDIT_DIR

    def log(
        self,
        intent: Any,
        tool_name: str,
        tool_params: dict,
        query: str,
        cross_result: Any,
        policy_matches: list,
        decision: Any,
    ) -> dict[str, Any]:
        """构造审计记录，写入 JSONL 文件并返回记录。"""
        record: dict[str, Any] = {
            "call_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_query": query,
            "tool_name": tool_name,
            "tool_params": tool_params,
            "intent": intent.to_dict() if hasattr(intent, "to_dict") else {},
            "cross_validation": cross_result.to_dict() if hasattr(cross_result, "to_dict") else {},
            "policy_matches": [
                {"rule_name": m.rule_name, "effect": m.effect, "priority": m.priority}
                for m in policy_matches
            ],
            "decision": decision.to_dict() if hasattr(decision, "to_dict") else {},
        }

        if self._enabled:
            self._write(record)

        return record

    def _write(self, record: dict[str, Any]) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        log_file = self._output_dir / "audit.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
