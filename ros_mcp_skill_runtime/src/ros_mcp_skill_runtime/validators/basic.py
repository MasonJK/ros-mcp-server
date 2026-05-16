"""Basic static validator for MVP dry runs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from ros_mcp_skill_runtime.backends.base import RobotBackend
from ros_mcp_skill_runtime.models import SkillManifest, SkillValidationCheck, SkillValidationResult
from ros_mcp_skill_runtime.permissions import PermissionChecker


class Validator(ABC):
    @abstractmethod
    async def validate(
        self, skill: SkillManifest, args: dict[str, Any], backend: RobotBackend
    ) -> SkillValidationResult: ...


class BasicValidator(Validator):
    def __init__(self, permission_checker: PermissionChecker | None = None):
        self.permission_checker = permission_checker or PermissionChecker()

    async def validate(self, skill: SkillManifest, args: dict[str, Any], backend: RobotBackend) -> SkillValidationResult:
        checks: list[SkillValidationCheck] = []
        checks.append(self.permission_checker.check(skill))
        checks.append(_validate_input_schema(skill, args))
        checks.append(_validate_executor(skill))
        checks.extend(await _validate_requirements(skill, backend))
        checks.extend(_run_named_static_checks(skill, args))
        valid = all(check.passed for check in checks)
        error = None if valid else "; ".join(check.message or check.name for check in checks if not check.passed)
        return SkillValidationResult(skill_name=skill.name, valid=valid, checks=checks, error=error)


def apply_defaults(skill: SkillManifest, args: dict[str, Any]) -> dict[str, Any]:
    merged = dict(args)
    for name, schema in skill.inputs.properties.items():
        if name not in merged and isinstance(schema, dict) and "default" in schema:
            merged[name] = schema["default"]
    return merged


def _validate_input_schema(skill: SkillManifest, args: dict[str, Any]) -> SkillValidationCheck:
    schema = skill.inputs.model_dump(exclude_none=True)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(args), key=lambda error: list(error.path))
    if errors:
        return SkillValidationCheck(
            name="input_schema",
            passed=False,
            message="; ".join(error.message for error in errors),
            details={"errors": [error.message for error in errors]},
        )
    return SkillValidationCheck(name="input_schema", passed=True, message=None, details={})


def _validate_executor(skill: SkillManifest) -> SkillValidationCheck:
    executor = skill.executor
    missing: list[str] = []
    if executor.type == "topic":
        missing = [name for name in ("topic_name", "message_type") if getattr(executor, name) is None]
    elif executor.type == "service":
        missing = [name for name in ("service_name", "service_type") if getattr(executor, name) is None]
    elif executor.type == "action":
        missing = [name for name in ("action_name", "action_type") if getattr(executor, name) is None]
    if missing:
        return SkillValidationCheck(
            name="executor_config",
            passed=False,
            message=f"executor missing required fields: {', '.join(missing)}",
            details={"missing": missing},
        )
    return SkillValidationCheck(name="executor_config", passed=True, message=None, details={})


async def _validate_requirements(skill: SkillManifest, backend: RobotBackend) -> list[SkillValidationCheck]:
    checks: list[SkillValidationCheck] = []
    try:
        topics = {item.get("name") for item in await backend.list_topics()}
        services = {item.get("name") for item in await backend.list_services()}
        actions = {item.get("name") for item in await backend.list_actions()}
    except Exception as exc:  # noqa: BLE001 - validation should report backend failures clearly.
        return [SkillValidationCheck(name="backend_requirements", passed=False, message=str(exc), details={})]

    required_topics = set(skill.requires.topics_read + skill.requires.topics_write)
    required_services = set(skill.requires.services)
    required_actions = set(skill.requires.actions)
    checks.append(_availability_check("required_topics", required_topics, topics))
    checks.append(_availability_check("required_services", required_services, services))
    checks.append(_availability_check("required_actions", required_actions, actions))
    return checks


def _availability_check(name: str, required: set[str], available: set[str]) -> SkillValidationCheck:
    missing = sorted(item for item in required if item not in available)
    return SkillValidationCheck(
        name=name,
        passed=not missing,
        message=None if not missing else f"missing {name}: {', '.join(missing)}",
        details={"required": sorted(required), "missing": missing},
    )


def _run_named_static_checks(skill: SkillManifest, args: dict[str, Any]) -> list[SkillValidationCheck]:
    merged = apply_defaults(skill, args)
    checks: list[SkillValidationCheck] = []
    for check_name in skill.validation.checks:
        if check_name in {"permission_check", "controller_available"}:
            continue
        if check_name in {"duration_bounds", "velocity_bounds", "joint_count_matches", "joint_limits"}:
            checks.append(_schema_backed_check(check_name, skill, merged))
        else:
            checks.append(SkillValidationCheck(name=check_name, passed=True, message="check stub passed", details={}))
    return checks


def _schema_backed_check(check_name: str, skill: SkillManifest, args: dict[str, Any]) -> SkillValidationCheck:
    schema = skill.inputs.model_dump(exclude_none=True)
    errors: list[ValidationError] = []
    for error in Draft202012Validator(schema).iter_errors(args):
        path = list(error.path)
        if check_name == "duration_bounds" and path and path[0] == "duration_sec":
            errors.append(error)
        elif check_name == "velocity_bounds" and path and ("velocity" in str(path[0]) or str(path[0]) in {"linear_x", "angular_z"}):
            errors.append(error)
        elif check_name in {"joint_count_matches", "joint_limits"} and path and path[0] == "joint_positions":
            errors.append(error)
    if errors:
        return SkillValidationCheck(
            name=check_name,
            passed=False,
            message="; ".join(error.message for error in errors),
            details={"errors": [error.message for error in errors]},
        )
    return SkillValidationCheck(name=check_name, passed=True, message=None, details={})


class SimulationValidator:
    async def validate_trajectory(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


class IsaacSimValidator(SimulationValidator):
    pass


class MuJoCoValidator(SimulationValidator):
    pass


class MoveItValidator(SimulationValidator):
    pass
