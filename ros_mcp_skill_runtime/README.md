# ROS-MCP Skill Runtime

ROS-MCP Skill Runtime is a minimal robot skill layer that sits above ROS-MCP. It lets Claude, Codex, and other MCP-compatible clients call safe, named robot skills instead of directly publishing arbitrary ROS topics, calling arbitrary services, or sending arbitrary action goals.

## Why skills instead of raw ROS tools?

Raw ROS access is powerful but too low-level for default agent control. This runtime exposes a constrained public interface:

- `list_skills()`
- `describe_skill(skill_name)`
- `dry_run_skill(skill_name, args)`
- `execute_skill(skill_name, args)`
- `get_robot_state()`
- `stop_robot()`

Raw topic/service/action operations are internal backend methods used only after registry lookup, permission checks, and validation.

## Architecture

```text
Claude / Codex / MCP Client
        ↓
Skill Runtime MCP Server
        ↓
Skill registry + validation + permissions + JSONL logging
        ↓
MockBackend or RosMcpBackend
        ↓
ROS-MCP / rosbridge / ROS 2
        ↓
Robot or simulator
```

## Installation

```bash
cd ros_mcp_skill_runtime
uv sync --extra dev
```

Or from this repository with the existing virtual environment:

```bash
cd ros_mcp_skill_runtime
PYTHONPATH=src ../.venv/bin/python -m pytest
```

## How to test this out

Start with the mock backend. It does not require ROS, turtlesim, rosbridge, or a physical robot, so it is the safest way to verify the runtime behavior before trying a live simulator.

### 1. Run unit tests and lint

From the package directory:

```bash
cd ros_mcp_skill_runtime
PYTHONPATH=src python -m pytest
ruff check src tests
```

On Windows PowerShell, set `PYTHONPATH` first:

```powershell
cd ros_mcp_skill_runtime
$env:PYTHONPATH = "src"
python -m pytest
ruff check src tests
```

Expected result: all tests pass and `ruff` reports no lint failures. These checks cover manifest loading, duplicate and invalid manifest rejection, permission behavior, input validation, mock execution, JSONL log writing, and `stop_robot()` behavior.

### 2. Run a no-ROS smoke test from Python

This exercises the runtime directly without needing an MCP client:

```bash
cd ros_mcp_skill_runtime
PYTHONPATH=src python - <<'PYTHON_SMOKE'
import asyncio
from pathlib import Path

from ros_mcp_skill_runtime.backends.mock_backend import MockBackend
from ros_mcp_skill_runtime.logging_utils import JsonlEventLogger
from ros_mcp_skill_runtime.permissions import PermissionChecker, PermissionPolicy
from ros_mcp_skill_runtime.registry import SkillRegistry
from ros_mcp_skill_runtime.runtime import SkillRuntime
from ros_mcp_skill_runtime.validators.basic import BasicValidator

runtime = SkillRuntime(
    registry=SkillRegistry(["skills/arm_basic"]),
    backend=MockBackend(),
    logger=JsonlEventLogger("logs/manual_smoke_test.jsonl"),
    validator=BasicValidator(PermissionChecker(PermissionPolicy())),
)

async def main():
    print("SKILLS", runtime.list_skills())
    print("DESCRIBE", runtime.describe_skill("move_to_joint_positions")["name"])
    valid = await runtime.dry_run_skill(
        "move_to_joint_positions",
        {"joint_positions": [0, 0, 0, 0, 0, 0]},
    )
    print("VALID DRY RUN", valid.model_dump(mode="json"))
    invalid = await runtime.dry_run_skill(
        "move_to_joint_positions",
        {"joint_positions": [0, 0]},
    )
    print("INVALID DRY RUN", invalid.model_dump(mode="json"))
    executed = await runtime.execute_skill(
        "move_to_joint_positions",
        {"joint_positions": [0, 0, 0, 0, 0, 0]},
    )
    print("EXECUTED", executed.model_dump(mode="json"))
    print("STATE", await runtime.get_robot_state())
    print("STOP", await runtime.stop_robot())
    print("LOG_EXISTS", Path("logs/manual_smoke_test.jsonl").exists())

asyncio.run(main())
PYTHON_SMOKE
```

Expected result:

- `list_skills` includes arm skills such as `move_to_joint_positions`, `move_arm_home`, gripper skills, `get_robot_state`, and `stop_robot`.
- The valid dry-run returns `valid: true`.
- The invalid dry-run with only two joints returns `valid: false` and mentions the joint array length.
- The execute call returns `success: true` with `execution_backend: mock`.
- `logs/manual_smoke_test.jsonl` is created.

### 3. Run the MCP server with the mock backend

```bash
cd ros_mcp_skill_runtime
uv run ros-mcp-skill-runtime \
  --backend mock \
  --skills skills/arm_basic \
  --config configs/runtime.yaml \
  --log-path logs/skill_events.jsonl
```

Then connect your MCP client to the server using the stdio configuration below. In the client, call these tools in order:

```text
list_skills()
describe_skill("move_to_joint_positions")
dry_run_skill("move_to_joint_positions", {"joint_positions": [0,0,0,0,0,0]})
dry_run_skill("move_to_joint_positions", {"joint_positions": [0,0]})
execute_skill("move_to_joint_positions", {"joint_positions": [0,0,0,0,0,0]})
get_robot_state()
stop_robot()
```

Expected result: the MCP client only sees skill-level robot tools, validation rejects the bad joint vector before execution, and `logs/skill_events.jsonl` contains one JSON record per dry-run or execution.

### 4. Optional turtlesim test with ROS-MCP

Only run this after the mock backend works and you have ROS 2, turtlesim, rosbridge, and ROS-MCP available:

```bash
# Terminal 1
ros2 run turtlesim turtlesim_node

# Terminal 2
ros2 launch rosbridge_server rosbridge_websocket_launch.xml

# Terminal 3
uvx ros-mcp --transport=stdio

# Terminal 4
cd ros_mcp_skill_runtime
uv run ros-mcp-skill-runtime \
  --backend ros_mcp \
  --skills skills/turtlesim \
  --config configs/runtime.yaml
```

From your MCP client, test:

```text
list_skills()
dry_run_skill("move_forward", {"linear_x": 1.0, "duration_sec": 1.0})
dry_run_skill("move_forward", {"linear_x": 99.0, "duration_sec": 1.0})
execute_skill("move_forward", {"linear_x": 1.0, "duration_sec": 1.0})
execute_skill("rotate", {"angular_z": 1.0, "duration_sec": 1.0})
stop_robot()
```

Expected result: invalid velocity is rejected, valid movement commands publish through ROS-MCP, and stop publishes a zero velocity command. The current `RosMcpBackend` is an MVP skeleton; topic and service operations are the intended first integration path, while action-goal forwarding intentionally fails clearly until a robust upstream action bridge is added.

## What you should test

Use this checklist when reviewing changes or trying the runtime manually:

- **Skill discovery:** `list_skills()` returns only named skills, not raw ROS topic/service/action tools.
- **Skill description:** `describe_skill("move_to_joint_positions")` returns the YAML-derived manifest with inputs, requirements, validation checks, executor config, and logging config.
- **Good dry-run:** a valid six-joint arm command passes validation.
- **Bad dry-run:** a malformed arm command such as `{"joint_positions": [0, 0]}` fails validation and does not execute.
- **Numeric bounds:** turtlesim `linear_x: 99.0` or an arm joint outside `[-3.14, 3.14]` fails validation.
- **Permission behavior:** a `commit` safety-tier skill is rejected with `human approval not implemented`.
- **Mock execution:** valid mock execution returns `success: true`, `validation_passed: true`, and `execution_backend: mock`.
- **Stop behavior:** `stop_robot()` executes the configured stop skill when present, or returns `stop not configured` instead of guessing unsafe behavior.
- **Logging:** every dry-run and execution appends JSONL records containing timestamp, event type, skill name, args, validation, result, and backend.
- **Safety boundary:** no public MCP tool should allow arbitrary shell execution, arbitrary topic publishing, arbitrary service calls, arbitrary action goals, or validation bypass.

## Mock backend demo

No ROS is required:

```bash
cd ros_mcp_skill_runtime
uv run ros-mcp-skill-runtime \
  --backend mock \
  --skills skills/arm_basic \
  --config configs/runtime.yaml
```

Example MCP calls:

```text
list_skills()
describe_skill("move_to_joint_positions")
dry_run_skill("move_to_joint_positions", {"joint_positions": [0,0,0,0,0,0]})
execute_skill("move_to_joint_positions", {"joint_positions": [0,0,0,0,0,0]})
get_robot_state()
stop_robot()
```

Logs are written to `logs/skill_events.jsonl` by default. A sample file is included at `logs/skill_events.example.jsonl`.

## Turtlesim demo

```bash
# Terminal 1
ros2 run turtlesim turtlesim_node

# Terminal 2
ros2 launch rosbridge_server rosbridge_websocket_launch.xml

# Terminal 3
uvx ros-mcp --transport=stdio

# Terminal 4
cd ros_mcp_skill_runtime
uv run ros-mcp-skill-runtime \
  --backend ros_mcp \
  --skills skills/turtlesim \
  --config configs/runtime.yaml
```

Expected MCP flow:

```text
list_skills()
dry_run_skill("move_forward", {"linear_x": 1.0, "duration_sec": 1.0})
execute_skill("move_forward", {"linear_x": 1.0, "duration_sec": 1.0})
execute_skill("rotate", {"angular_z": 1.0, "duration_sec": 1.0})
stop_robot()
```

## MCP client configuration

Example stdio configuration:

```json
{
  "mcpServers": {
    "ros-mcp-skill-runtime": {
      "command": "uv",
      "args": [
        "run",
        "ros-mcp-skill-runtime",
        "--backend",
        "mock",
        "--skills",
        "skills/arm_basic",
        "--config",
        "configs/runtime.yaml"
      ],
      "cwd": "/absolute/path/to/ros_mcp_skill_runtime"
    }
  }
}
```

## Skill manifest format

A skill is a YAML manifest with `name`, `description`, `safety_tier`, `inputs`, `requires`, `validation`, `executor`, and `logging`.

```yaml
name: move_forward
description: Move turtlesim forward for a short duration.
safety_tier: act
inputs:
  type: object
  properties:
    linear_x: {type: number, default: 1.0, minimum: 0.0, maximum: 2.0}
    duration_sec: {type: number, default: 1.0, minimum: 0.1, maximum: 5.0}
requires:
  topics_read: []
  topics_write: [/turtle1/cmd_vel]
  services: []
  actions: []
validation:
  checks: [duration_bounds, velocity_bounds]
executor:
  backend: ros_mcp
  type: topic
  topic_name: /turtle1/cmd_vel
  message_type: geometry_msgs/Twist
logging:
  record_before_state: true
  record_after_state: true
  record_result: true
```

To add a skill, place a `.yaml` file in an allowed skill directory, constrain all inputs with JSON Schema fields, declare required ROS resources, and choose a `topic`, `service`, `action`, or `state` executor.

## Safety limitations

MVP policy:

- `observe`, `prepare`, and validated `act` skills are allowed.
- `commit` skills are rejected with `human approval not implemented`.
- Public tools do not expose arbitrary shell, topic publishing, service calls, action goals, or validation bypass.
- Dry-run is static validation only; it is not physics simulation.
- `RosMcpBackend` is intentionally a skeleton for topic/service operations and clear action-goal failure until a robust upstream action bridge is selected.

## Roadmap

- Direct ROS 2 backend
- Isaac Sim validator
- MoveIt 2 validator
- MuJoCo validator
- LeRobot / RLDS / rosbag exporters
- VLA policy adapters
- Human approval provider
- Multi-robot scheduling
