"""Data models for the ROS-MCP skill runtime."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SafetyTier(str, Enum):
    OBSERVE = "observe"
    PREPARE = "prepare"
    ACT = "act"
    COMMIT = "commit"


class SkillInputSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = "object"
    required: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


class SkillRequirement(BaseModel):
    topics_read: list[str] = Field(default_factory=list)
    topics_write: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)


class SkillValidationConfig(BaseModel):
    checks: list[str] = Field(default_factory=list)


class SkillExecutorConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    backend: str = "ros_mcp"
    type: Literal["topic", "service", "action", "state"]
    topic_name: str | None = None
    message_type: str | None = None
    service_name: str | None = None
    service_type: str | None = None
    action_name: str | None = None
    action_type: str | None = None
    fixed_message: dict[str, Any] | None = None
    fixed_request: dict[str, Any] | None = None
    fixed_goal: dict[str, Any] | None = None
    stop_message: dict[str, Any] | None = None


class SkillLoggingConfig(BaseModel):
    record_before_state: bool = True
    record_after_state: bool = True
    record_result: bool = True


class SkillManifest(BaseModel):
    name: str
    description: str
    safety_tier: SafetyTier
    inputs: SkillInputSchema
    requires: SkillRequirement
    validation: SkillValidationConfig
    executor: SkillExecutorConfig
    logging: SkillLoggingConfig
    source_path: str | None = None

    @field_validator("name")
    @classmethod
    def name_must_be_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("skill name cannot be empty")
        return value

    def summary(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "safety_tier": self.safety_tier.value,
        }


class SkillExecutionRequest(BaseModel):
    skill_name: str
    args: dict[str, Any] = Field(default_factory=dict)


class SkillValidationCheck(BaseModel):
    name: str
    passed: bool
    message: str | None = None
    details: dict[str, Any] | None = Field(default_factory=dict)


class SkillValidationResult(BaseModel):
    skill_name: str
    valid: bool
    checks: list[SkillValidationCheck] = Field(default_factory=list)
    error: str | None = None


class SkillExecutionResult(BaseModel):
    success: bool
    skill_name: str
    args: dict[str, Any]
    started_at: str
    finished_at: str
    validation_passed: bool
    execution_backend: str
    result: dict[str, Any] | None = None
    error: str | None = None
    logs_path: str | None = None


class RobotState(BaseModel):
    backend: str
    status: str = "unknown"
    data: dict[str, Any] = Field(default_factory=dict)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def path_to_str(path: str | Path) -> str:
    return str(Path(path))
