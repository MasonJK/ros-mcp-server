"""Mock backend for tests and demos without ROS."""

from __future__ import annotations

from typing import Any

from ros_mcp_skill_runtime.backends.base import RobotBackend


class MockBackend(RobotBackend):
    name = "mock"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._state = {
            "backend": "mock",
            "joint_states": {
                "names": [f"joint_{index}" for index in range(1, 7)],
                "positions": [0, 0, 0, 0, 0, 0],
                "velocities": [0, 0, 0, 0, 0, 0],
            },
            "turtlesim": {"pose": {"x": 5.5, "y": 5.5, "theta": 0.0}},
            "status": "ready",
        }

    async def get_robot_state(self) -> dict[str, Any]:
        return dict(self._state)

    async def list_topics(self) -> list[dict[str, Any]]:
        return [
            {"name": "/turtle1/cmd_vel", "type": "geometry_msgs/Twist"},
            {"name": "/turtle1/pose", "type": "turtlesim/Pose"},
            {"name": "/joint_states", "type": "sensor_msgs/msg/JointState"},
        ]

    async def list_services(self) -> list[dict[str, Any]]:
        return [
            {"name": "/reset", "type": "std_srvs/srv/Empty"},
            {"name": "/gripper/open", "type": "std_srvs/srv/Trigger"},
            {"name": "/gripper/close", "type": "std_srvs/srv/Trigger"},
            {"name": "/arm/stop", "type": "std_srvs/srv/Trigger"},
        ]

    async def list_actions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "/joint_trajectory_controller/follow_joint_trajectory",
                "type": "control_msgs/action/FollowJointTrajectory",
            }
        ]

    async def publish_topic(self, topic_name: str, message_type: str, message: dict[str, Any]) -> dict[str, Any]:
        call = {"operation": "publish_topic", "topic_name": topic_name, "message_type": message_type, "message": message}
        self.calls.append(call)
        return {"accepted": True, **call}

    async def call_service(self, service_name: str, service_type: str, request: dict[str, Any]) -> dict[str, Any]:
        call = {"operation": "call_service", "service_name": service_name, "service_type": service_type, "request": request}
        self.calls.append(call)
        return {"accepted": True, "response": {"success": True, "message": "mock service accepted"}, **call}

    async def send_action_goal(self, action_name: str, action_type: str, goal: dict[str, Any]) -> dict[str, Any]:
        call = {"operation": "send_action_goal", "action_name": action_name, "action_type": action_type, "goal": goal}
        self.calls.append(call)
        if action_name.endswith("follow_joint_trajectory") and "joint_positions" in goal:
            self._state["joint_states"]["positions"] = goal["joint_positions"]
        return {"accepted": True, "status": "succeeded", **call}
