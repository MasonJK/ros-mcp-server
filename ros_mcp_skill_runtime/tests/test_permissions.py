from pathlib import Path

from ros_mcp_skill_runtime.permissions import PermissionChecker, PermissionPolicy
from ros_mcp_skill_runtime.registry import SkillRegistry

ROOT = Path(__file__).resolve().parents[1]


def test_permission_rejects_disallowed_directory():
    registry = SkillRegistry([ROOT / "skills" / "arm_basic"])
    policy = PermissionPolicy(allowed_skill_dirs=[str(ROOT / "skills" / "turtlesim")])
    check = PermissionChecker(policy).check(registry.get_skill("move_to_joint_positions"))
    assert check.passed is False


def test_commit_tier_rejected_with_human_approval_message(tmp_path):
    manifest = """
name: dangerous
description: Dangerous.
safety_tier: commit
inputs: {type: object, properties: {}}
requires: {topics_read: [], topics_write: [], services: [], actions: []}
validation: {checks: []}
executor: {backend: mock, type: state}
logging: {record_before_state: false, record_after_state: false, record_result: true}
"""
    (tmp_path / "dangerous.yaml").write_text(manifest)
    registry = SkillRegistry([tmp_path])
    check = PermissionChecker(PermissionPolicy()).check(registry.get_skill("dangerous"))
    assert check.passed is False
    assert check.message == "human approval not implemented"
