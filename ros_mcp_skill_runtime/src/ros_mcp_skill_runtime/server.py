"""MCP server exposing skill-level robot tools only."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from ros_mcp_skill_runtime.backends.mock_backend import MockBackend
from ros_mcp_skill_runtime.backends.ros_mcp_backend import RosMcpBackend
from ros_mcp_skill_runtime.logging_utils import JsonlEventLogger
from ros_mcp_skill_runtime.permissions import PermissionChecker, PermissionPolicy
from ros_mcp_skill_runtime.registry import SkillRegistry
from ros_mcp_skill_runtime.runtime import SkillRuntime
from ros_mcp_skill_runtime.validators.basic import BasicValidator

mcp = FastMCP("ros-mcp-skill-runtime")
_runtime: SkillRuntime | None = None


def build_runtime(args: argparse.Namespace) -> SkillRuntime:
    backend = MockBackend() if args.backend == "mock" else RosMcpBackend()
    policy = PermissionPolicy.from_yaml(args.config) if args.config else PermissionPolicy()
    if policy.allowed_skill_dirs:
        # Resolve config-relative skill dirs for demos launched from the package root.
        config_parent = Path(args.config).parent if args.config else Path.cwd()
        policy.allowed_skill_dirs = [str((config_parent / ".." / path).resolve()) if not Path(path).is_absolute() else path for path in policy.allowed_skill_dirs]
    registry = SkillRegistry(args.skills)
    logger = JsonlEventLogger(args.log_path)
    validator = BasicValidator(PermissionChecker(policy))
    return SkillRuntime(registry=registry, backend=backend, logger=logger, validator=validator)


def get_runtime() -> SkillRuntime:
    if _runtime is None:
        raise RuntimeError("Skill runtime is not initialized")
    return _runtime


@mcp.tool(description="List safe, named robot skills available to this MCP server.")
def list_skills() -> list[dict[str, str]]:
    return get_runtime().list_skills()


@mcp.tool(description="Describe one robot skill manifest by name.")
def describe_skill(skill_name: str) -> dict[str, Any]:
    return get_runtime().describe_skill(skill_name)


@mcp.tool(description="Validate a robot skill without executing it.")
async def dry_run_skill(skill_name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    result = await get_runtime().dry_run_skill(skill_name, args or {})
    return result.model_dump(mode="json")


@mcp.tool(description="Execute an allowlisted robot skill after validation passes.")
async def execute_skill(skill_name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    result = await get_runtime().execute_skill(skill_name, args or {})
    return result.model_dump(mode="json")


@mcp.tool(description="Inspect robot state through the configured backend.")
async def get_robot_state() -> dict[str, Any]:
    return await get_runtime().get_robot_state()


@mcp.tool(description="Stop the robot with a configured safe stop skill, or return stop-not-configured.")
async def stop_robot() -> dict[str, Any]:
    return await get_runtime().stop_robot()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ROS-MCP Skill Runtime MCP server")
    parser.add_argument("--backend", choices=["mock", "ros_mcp"], default="mock")
    parser.add_argument("--skills", nargs="+", default=["skills/arm_basic"])
    parser.add_argument("--config", default=None)
    parser.add_argument("--log-path", default="logs/skill_events.jsonl")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--reload-skills", action="store_true", help="Accepted for future hot reload support")
    parser.add_argument("--transport", choices=["stdio", "http", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9001)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    global _runtime
    args = parse_args(argv)
    _runtime = build_runtime(args)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
