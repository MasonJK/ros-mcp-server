"""Skill manifest registry and YAML loader."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml
from pydantic import ValidationError

from ros_mcp_skill_runtime.models import SkillManifest


class SkillRegistryError(ValueError):
    """Raised when skill manifests cannot be loaded."""


class SkillRegistry:
    """Load, validate, and describe skill manifests from one or more directories."""

    def __init__(self, skill_dirs: Iterable[str | Path]):
        self.skill_dirs = [Path(path) for path in skill_dirs]
        self._skills: dict[str, SkillManifest] = {}
        self.reload()

    def reload(self) -> None:
        skills: dict[str, SkillManifest] = {}
        for skill_dir in self.skill_dirs:
            if not skill_dir.exists():
                raise SkillRegistryError(f"Skill directory does not exist: {skill_dir}")
            for manifest_path in sorted(skill_dir.rglob("*.yaml")):
                skill = self._load_manifest(manifest_path)
                if skill.name in skills:
                    previous = skills[skill.name].source_path
                    raise SkillRegistryError(
                        f"Duplicate skill name '{skill.name}' in {manifest_path} and {previous}"
                    )
                skills[skill.name] = skill
        self._skills = skills

    def _load_manifest(self, manifest_path: Path) -> SkillManifest:
        try:
            data = yaml.safe_load(manifest_path.read_text())
        except yaml.YAMLError as exc:
            raise SkillRegistryError(f"Invalid YAML in {manifest_path}: {exc}") from exc
        except OSError as exc:
            raise SkillRegistryError(f"Cannot read skill manifest {manifest_path}: {exc}") from exc

        if not isinstance(data, dict):
            raise SkillRegistryError(f"Invalid manifest {manifest_path}: top-level YAML must be an object")
        data["source_path"] = str(manifest_path)
        try:
            return SkillManifest.model_validate(data)
        except ValidationError as exc:
            raise SkillRegistryError(f"Invalid skill manifest {manifest_path}: {exc}") from exc

    def list_skills(self) -> list[dict[str, str]]:
        return [skill.summary() for skill in sorted(self._skills.values(), key=lambda item: item.name)]

    def describe_skill(self, skill_name: str) -> dict:
        return self.get_skill(skill_name).model_dump(mode="json")

    def get_skill(self, skill_name: str) -> SkillManifest:
        try:
            return self._skills[skill_name]
        except KeyError as exc:
            raise SkillRegistryError(f"Skill not found: {skill_name}") from exc

    @property
    def skills(self) -> dict[str, SkillManifest]:
        return dict(self._skills)
