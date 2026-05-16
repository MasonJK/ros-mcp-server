"""Action skill executor."""

from __future__ import annotations

from typing import Any

from ros_mcp_skill_runtime.backends.base import RobotBackend
from ros_mcp_skill_runtime.models import SkillManifest


async def execute_action_skill(skill: SkillManifest, args: dict[str, Any], backend: RobotBackend) -> dict[str, Any]:
    executor = skill.executor
    goal = executor.fixed_goal or dict(args)
    return await backend.send_action_goal(executor.action_name or "", executor.action_type or "", goal)
