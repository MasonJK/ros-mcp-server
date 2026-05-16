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
