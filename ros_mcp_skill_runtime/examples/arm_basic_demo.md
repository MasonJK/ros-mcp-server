# Arm Basic Mock Demo

This demo requires no ROS.

```bash
cd ros_mcp_skill_runtime
uv run ros-mcp-skill-runtime --backend mock --skills skills/arm_basic --config configs/runtime.yaml
```

Expected MCP flow:

1. `list_skills()`
2. `describe_skill("move_to_joint_positions")`
3. `dry_run_skill("move_to_joint_positions", {"joint_positions": [0,0,0,0,0,0]})`
4. `execute_skill("move_to_joint_positions", {"joint_positions": [0,0,0,0,0,0]})`
5. `get_robot_state()`
6. `stop_robot()`

Invalid vectors such as `[0, 0]` are rejected during dry-run and execution.
