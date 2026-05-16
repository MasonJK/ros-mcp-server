"""Topic skill executor."""

from __future__ import annotations

import asyncio
from typing import Any

from ros_mcp_skill_runtime.backends.base import RobotBackend
from ros_mcp_skill_runtime.models import SkillManifest

ZERO_TWIST = {
    "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
    "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
}


async def execute_topic_skill(skill: SkillManifest, args: dict[str, Any], backend: RobotBackend) -> dict[str, Any]:
    executor = skill.executor
    message = executor.fixed_message or _message_from_args(args)
    result = await backend.publish_topic(executor.topic_name or "", executor.message_type or "", message)
    duration = args.get("duration_sec")
    if duration is not None and duration > 0:
        await asyncio.sleep(float(duration))
        stop_message = executor.stop_message or ZERO_TWIST
        stop_result = await backend.publish_topic(executor.topic_name or "", executor.message_type or "", stop_message)
        result = {"active_publish": result, "stop_publish": stop_result}
    return result


def _message_from_args(args: dict[str, Any]) -> dict[str, Any]:
    if "linear_x" in args or "angular_z" in args:
        return {
            "linear": {"x": float(args.get("linear_x", 0.0)), "y": 0.0, "z": 0.0},
            "angular": {"x": 0.0, "y": 0.0, "z": float(args.get("angular_z", 0.0))},
        }
    return dict(args)
