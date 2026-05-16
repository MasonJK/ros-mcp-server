import asyncio
from pathlib import Path

from ros_mcp_skill_runtime.backends.mock_backend import MockBackend
from ros_mcp_skill_runtime.permissions import PermissionChecker, PermissionPolicy
from ros_mcp_skill_runtime.registry import SkillRegistry
from ros_mcp_skill_runtime.validators.basic import BasicValidator

ROOT = Path(__file__).resolve().parents[1]


def test_dry_run_success():
    registry = SkillRegistry([ROOT / "skills" / "arm_basic"])
    validator = BasicValidator(PermissionChecker(PermissionPolicy()))
    result = asyncio.run(validator.validate(
        registry.get_skill("move_to_joint_positions"),
        {"joint_positions": [0, 0, 0, 0, 0, 0], "duration_sec": 1.0},
        MockBackend(),
    ))
    assert result.valid is True


def test_input_schema_rejects_bad_joint_count():
    registry = SkillRegistry([ROOT / "skills" / "arm_basic"])
    validator = BasicValidator(PermissionChecker(PermissionPolicy()))
    result = asyncio.run(validator.validate(
        registry.get_skill("move_to_joint_positions"),
        {"joint_positions": [0, 0], "duration_sec": 1.0},
        MockBackend(),
    ))
    assert result.valid is False
    assert "too short" in (result.error or "")


def test_numeric_bounds_rejected():
    registry = SkillRegistry([ROOT / "skills" / "turtlesim"])
    validator = BasicValidator(PermissionChecker(PermissionPolicy()))
    result = asyncio.run(validator.validate(
        registry.get_skill("move_forward"),
        {"linear_x": 99, "duration_sec": 1.0},
        MockBackend(),
    ))
    assert result.valid is False
    assert any(check.name == "velocity_bounds" and not check.passed for check in result.checks)
