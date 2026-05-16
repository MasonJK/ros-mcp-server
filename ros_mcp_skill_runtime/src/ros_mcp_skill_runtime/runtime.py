"""High-level skill runtime orchestration."""

from __future__ import annotations

from typing import Any

from ros_mcp_skill_runtime.backends.base import RobotBackend
from ros_mcp_skill_runtime.executors.action_executor import execute_action_skill
from ros_mcp_skill_runtime.executors.service_executor import execute_service_skill
from ros_mcp_skill_runtime.executors.topic_executor import execute_topic_skill
from ros_mcp_skill_runtime.logging_utils import JsonlEventLogger
from ros_mcp_skill_runtime.models import SkillExecutionResult, SkillManifest, utc_now
from ros_mcp_skill_runtime.registry import SkillRegistry, SkillRegistryError
from ros_mcp_skill_runtime.validators.basic import BasicValidator, apply_defaults


class SkillRuntime:
    def __init__(self, registry: SkillRegistry, backend: RobotBackend, logger: JsonlEventLogger, validator: BasicValidator):
        self.registry = registry
        self.backend = backend
        self.logger = logger
        self.validator = validator

    def list_skills(self) -> list[dict[str, str]]:
        return self.registry.list_skills()

    def describe_skill(self, skill_name: str) -> dict[str, Any]:
        return self.registry.describe_skill(skill_name)

    async def dry_run_skill(self, skill_name: str, args: dict[str, Any] | None = None):
        args = args or {}
        skill = self.registry.get_skill(skill_name)
        merged_args = apply_defaults(skill, args)
        validation = await self.validator.validate(skill, merged_args, self.backend)
        self.logger.write_event("dry_run", skill_name, merged_args, validation, None, self.backend.name)
        return validation

    async def execute_skill(self, skill_name: str, args: dict[str, Any] | None = None) -> SkillExecutionResult:
        args = args or {}
        skill = self.registry.get_skill(skill_name)
        merged_args = apply_defaults(skill, args)
        started_at = utc_now()
        validation = await self.validator.validate(skill, merged_args, self.backend)
        if not validation.valid:
            finished_at = utc_now()
            result = SkillExecutionResult(
                success=False,
                skill_name=skill.name,
                args=merged_args,
                started_at=started_at,
                finished_at=finished_at,
                validation_passed=False,
                execution_backend=self.backend.name,
                result=None,
                error=validation.error,
                logs_path=None,
            )
            logs_path = self.logger.write_event("execute", skill_name, merged_args, validation, result, self.backend.name)
            result.logs_path = logs_path
            return result
        try:
            backend_result = await self._execute_validated_skill(skill, merged_args)
            success = True
            error = None
        except Exception as exc:  # noqa: BLE001 - execution result must preserve failures structurally.
            backend_result = None
            success = False
            error = str(exc)
        finished_at = utc_now()
        result = SkillExecutionResult(
            success=success,
            skill_name=skill.name,
            args=merged_args,
            started_at=started_at,
            finished_at=finished_at,
            validation_passed=True,
            execution_backend=self.backend.name,
            result=backend_result,
            error=error,
            logs_path=None,
        )
        logs_path = self.logger.write_event("execute", skill_name, merged_args, validation, result, self.backend.name)
        result.logs_path = logs_path
        return result

    async def _execute_validated_skill(self, skill: SkillManifest, args: dict[str, Any]) -> dict[str, Any]:
        if skill.executor.type == "topic":
            return await execute_topic_skill(skill, args, self.backend)
        if skill.executor.type == "service":
            return await execute_service_skill(skill, args, self.backend)
        if skill.executor.type == "action":
            return await execute_action_skill(skill, args, self.backend)
        if skill.executor.type == "state":
            return await self.backend.get_robot_state()
        raise ValueError(f"Unsupported executor type: {skill.executor.type}")

    async def get_robot_state(self) -> dict[str, Any]:
        return await self.backend.get_robot_state()

    async def stop_robot(self) -> dict[str, Any]:
        for candidate in ("stop_robot", "stop"):
            try:
                return (await self.execute_skill(candidate, {})).model_dump(mode="json")
            except SkillRegistryError:
                continue
        return {"success": True, "message": "stop not configured", "backend": self.backend.name}
