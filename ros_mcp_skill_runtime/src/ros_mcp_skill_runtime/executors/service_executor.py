"""Service skill executor."""

from __future__ import annotations

from typing import Any

from ros_mcp_skill_runtime.backends.base import RobotBackend
from ros_mcp_skill_runtime.models import SkillManifest


async def execute_service_skill(skill: SkillManifest, args: dict[str, Any], backend: RobotBackend) -> dict[str, Any]:
    executor = skill.executor
    request = executor.fixed_request or dict(args)
    return await backend.call_service(executor.service_name or "", executor.service_type or "", request)
