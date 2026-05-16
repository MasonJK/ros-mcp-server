"""ROS-MCP backend adapter.

This adapter intentionally isolates ROS-MCP-specific raw operations from the public skill runtime
interface. Public MCP tools call skills; skills call this backend only after permission and validation.
"""

from __future__ import annotations

import asyncio
from typing import Any

from ros_mcp_skill_runtime.backends.base import RobotBackend


class RosMcpBackendError(RuntimeError):
    """Raised when ROS-MCP is unavailable or a raw ROS operation fails."""


class RosMcpBackend(RobotBackend):
    name = "ros_mcp"

    def __init__(self, rosbridge_ip: str = "127.0.0.1", rosbridge_port: int = 9090, timeout: float = 5.0):
        try:
            from ros_mcp.utils.websocket import WebSocketManager
        except ImportError as exc:
            raise RosMcpBackendError(
                "ROS-MCP is not importable. Install ros-mcp or run with --backend mock."
            ) from exc
        self.ws_manager = WebSocketManager(rosbridge_ip, rosbridge_port, default_timeout=timeout)

    async def _request(self, message: dict[str, Any]) -> dict[str, Any]:
        def blocking_request() -> dict[str, Any]:
            with self.ws_manager:
                response = self.ws_manager.request(message)
            if not isinstance(response, dict):
                raise RosMcpBackendError(f"ROS-MCP returned non-dict response: {response!r}")
            if response.get("op") == "service_response" and response.get("result") is False:
                raise RosMcpBackendError(str(response))
            return response

        return await asyncio.to_thread(blocking_request)


    async def _send(self, message: dict[str, Any]) -> None:
        def blocking_send() -> None:
            with self.ws_manager:
                error = self.ws_manager.send(message)
            if error:
                raise RosMcpBackendError(error)

        await asyncio.to_thread(blocking_send)

    async def get_robot_state(self) -> dict[str, Any]:
        topics = await self.list_topics()
        services = await self.list_services()
        actions = await self.list_actions()
        return {"backend": self.name, "status": "connected", "topics": topics, "services": services, "actions": actions}

    async def list_topics(self) -> list[dict[str, Any]]:
        response = await self._request({"op": "call_service", "service": "/rosapi/topics", "type": "rosapi/Topics", "args": {}, "id": "skill_runtime_topics"})
        values = response.get("values", {})
        return [{"name": name, "type": typ} for name, typ in zip(values.get("topics", []), values.get("types", []))]

    async def list_services(self) -> list[dict[str, Any]]:
        response = await self._request({"op": "call_service", "service": "/rosapi/services", "type": "rosapi/Services", "args": {}, "id": "skill_runtime_services"})
        values = response.get("values", {})
        return [{"name": name, "type": ""} for name in values.get("services", [])]

    async def list_actions(self) -> list[dict[str, Any]]:
        return []

    async def publish_topic(self, topic_name: str, message_type: str, message: dict[str, Any]) -> dict[str, Any]:
        advertise = {"op": "advertise", "topic": topic_name, "type": message_type}
        publish = {"op": "publish", "topic": topic_name, "msg": message}
        await self._send(advertise)
        await self._send(publish)
        return {"accepted": True, "operation": "publish_topic", "topic_name": topic_name, "message_type": message_type}

    async def call_service(self, service_name: str, service_type: str, request: dict[str, Any]) -> dict[str, Any]:
        response = await self._request({"op": "call_service", "service": service_name, "type": service_type, "args": request})
        return {"accepted": True, "operation": "call_service", "service_name": service_name, "response": response}

    async def send_action_goal(self, action_name: str, action_type: str, goal: dict[str, Any]) -> dict[str, Any]:
        raise RosMcpBackendError(
            "ROS-MCP action-goal forwarding is not implemented in the MVP backend skeleton. "
            f"Cannot send {action_name} ({action_type})."
        )
