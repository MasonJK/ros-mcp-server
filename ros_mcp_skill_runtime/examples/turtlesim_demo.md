# Turtlesim Skill Runtime Demo

This demo exposes only skill-level MCP tools to the client.

```bash
ros2 run turtlesim turtlesim_node
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
uvx ros-mcp --transport=stdio
cd ros_mcp_skill_runtime
uv run ros-mcp-skill-runtime --backend ros_mcp --skills skills/turtlesim --config configs/runtime.yaml
```

Expected MCP flow:

1. `list_skills()`
2. `dry_run_skill("move_forward", {"linear_x": 1.0, "duration_sec": 1.0})`
3. `execute_skill("move_forward", {"linear_x": 1.0, "duration_sec": 1.0})`
4. `execute_skill("rotate", {"angular_z": 1.0, "duration_sec": 1.0})`
5. `stop_robot()`

No public MCP tool publishes arbitrary topics or calls arbitrary services.
