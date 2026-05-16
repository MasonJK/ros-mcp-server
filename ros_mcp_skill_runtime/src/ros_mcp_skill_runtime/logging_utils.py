"""JSONL event logging for dry-runs and executions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ros_mcp_skill_runtime.models import utc_now


class JsonlEventLogger:
    def __init__(self, log_path: str | Path = "logs/skill_events.jsonl") -> None:
        self.log_path = Path(log_path)

    def write_event(
        self,
        event_type: str,
        skill_name: str,
        args: dict[str, Any],
        validation: Any,
        result: Any,
        backend: str,
    ) -> str:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": utc_now(),
            "event_type": event_type,
            "skill_name": skill_name,
            "args": args,
            "validation": _dump(validation),
            "result": _dump(result),
            "backend": backend,
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return str(self.log_path)


def _dump(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value
