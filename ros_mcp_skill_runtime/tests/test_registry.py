from pathlib import Path

import pytest
from ros_mcp_skill_runtime.registry import SkillRegistry, SkillRegistryError

ROOT = Path(__file__).resolve().parents[1]


def test_loads_skill_manifests():
    registry = SkillRegistry([ROOT / "skills" / "turtlesim", ROOT / "skills" / "arm_basic"])
    names = {skill["name"] for skill in registry.list_skills()}
    assert {"move_forward", "rotate", "stop", "move_to_joint_positions", "stop_robot"} <= names


def test_duplicate_skill_rejected(tmp_path):
    manifest = """
name: dup
description: Duplicate.
safety_tier: observe
inputs: {type: object, properties: {}}
requires: {topics_read: [], topics_write: [], services: [], actions: []}
validation: {checks: []}
executor: {backend: mock, type: state}
logging: {record_before_state: false, record_after_state: false, record_result: true}
"""
    (tmp_path / "a.yaml").write_text(manifest)
    (tmp_path / "b.yaml").write_text(manifest)
    with pytest.raises(SkillRegistryError, match="Duplicate skill"):
        SkillRegistry([tmp_path])


def test_invalid_yaml_rejected(tmp_path):
    (tmp_path / "bad.yaml").write_text("name: [")
    with pytest.raises(SkillRegistryError, match="Invalid YAML"):
        SkillRegistry([tmp_path])
