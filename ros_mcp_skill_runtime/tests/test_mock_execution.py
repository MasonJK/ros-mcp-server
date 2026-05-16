import asyncio
import json
from pathlib import Path

from ros_mcp_skill_runtime.backends.mock_backend import MockBackend
from ros_mcp_skill_runtime.logging_utils import JsonlEventLogger
from ros_mcp_skill_runtime.permissions import PermissionChecker, PermissionPolicy
from ros_mcp_skill_runtime.registry import SkillRegistry
from ros_mcp_skill_runtime.runtime import SkillRuntime
from ros_mcp_skill_runtime.validators.basic import BasicValidator

ROOT = Path(__file__).resolve().parents[1]


def make_runtime(log_path):
    return SkillRuntime(
        registry=SkillRegistry([ROOT / "skills" / "arm_basic"]),
        backend=MockBackend(),
        logger=JsonlEventLogger(log_path),
        validator=BasicValidator(PermissionChecker(PermissionPolicy())),
    )


def test_mock_backend_execution_and_log_writing(tmp_path):
    log_path = tmp_path / "skill_events.jsonl"
    runtime = make_runtime(log_path)
    result = asyncio.run(runtime.execute_skill("move_to_joint_positions", {"joint_positions": [0, 0, 0, 0, 0, 0]}))
    assert result.success is True
    assert result.validation_passed is True
    records = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert records[-1]["event_type"] == "execute"
    assert records[-1]["skill_name"] == "move_to_joint_positions"


def test_dry_run_failure_logs(tmp_path):
    log_path = tmp_path / "skill_events.jsonl"
    runtime = make_runtime(log_path)
    result = asyncio.run(runtime.dry_run_skill("move_to_joint_positions", {"joint_positions": [0, 0]}))
    assert result.valid is False
    assert log_path.exists()


def test_stop_robot_behavior(tmp_path):
    runtime = make_runtime(tmp_path / "skill_events.jsonl")
    result = asyncio.run(runtime.stop_robot())
    assert result["success"] is True
    assert result["skill_name"] == "stop_robot"
