"""Allowlist-based permission checks for skill execution."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ros_mcp_skill_runtime.models import SafetyTier, SkillManifest, SkillValidationCheck


class PermissionPolicy(BaseModel):
    allowed_skill_dirs: list[str] = Field(default_factory=list)
    allow_raw_ros_tools: bool = False
    allowed_safety_tiers: list[SafetyTier] = Field(
        default_factory=lambda: [SafetyTier.OBSERVE, SafetyTier.PREPARE, SafetyTier.ACT]
    )
    reject_safety_tiers: list[SafetyTier] = Field(default_factory=lambda: [SafetyTier.COMMIT])

    @classmethod
    def from_yaml(cls, path: str | Path | None) -> "PermissionPolicy":
        if path is None:
            return cls()
        data = yaml.safe_load(Path(path).read_text()) or {}
        permissions = data.get("permissions", data)
        return cls.model_validate(permissions)


class PermissionChecker:
    def __init__(self, policy: PermissionPolicy | None = None):
        self.policy = policy or PermissionPolicy()

    def check(self, skill: SkillManifest) -> SkillValidationCheck:
        if skill.safety_tier in self.policy.reject_safety_tiers:
            return SkillValidationCheck(
                name="permission_check",
                passed=False,
                message="human approval not implemented",
                details={"safety_tier": skill.safety_tier.value},
            )
        if skill.safety_tier not in self.policy.allowed_safety_tiers:
            return SkillValidationCheck(
                name="permission_check",
                passed=False,
                message=f"safety tier '{skill.safety_tier.value}' is not allowed",
                details={"allowed_safety_tiers": [tier.value for tier in self.policy.allowed_safety_tiers]},
            )
        if self.policy.allowed_skill_dirs and skill.source_path:
            source = Path(skill.source_path).resolve()
            allowed = any(_is_relative_to(source, Path(path).resolve()) for path in self.policy.allowed_skill_dirs)
            if not allowed:
                return SkillValidationCheck(
                    name="permission_check",
                    passed=False,
                    message="skill manifest is outside allowed_skill_dirs",
                    details={"source_path": skill.source_path},
                )
        return SkillValidationCheck(name="permission_check", passed=True, message=None, details={})


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
