"""Backend abstraction for robot connectivity."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RobotBackend(ABC):
    name: str = "base"

    @abstractmethod
    async def get_robot_state(self) -> dict[str, Any]: ...

    @abstractmethod
    async def list_topics(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def list_services(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def list_actions(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def publish_topic(self, topic_name: str, message_type: str, message: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    async def call_service(self, service_name: str, service_type: str, request: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    async def send_action_goal(self, action_name: str, action_type: str, goal: dict[str, Any]) -> dict[str, Any]: ...
