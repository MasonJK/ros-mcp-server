"""Future extension interfaces, intentionally inactive for the MVP."""

from __future__ import annotations

from typing import Any


class DatasetExporter:
    async def export_episode(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


class LeRobotExporter(DatasetExporter):
    pass


class RLDSExporter(DatasetExporter):
    pass


class RosbagExporter(DatasetExporter):
    pass


class PolicyAdapter:
    async def propose_action_chunk(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


class DiffusionPolicyAdapter(PolicyAdapter):
    pass


class ACTAdapter(PolicyAdapter):
    pass


class Pi0Adapter(PolicyAdapter):
    pass


class OpenVLAAdapter(PolicyAdapter):
    pass


class HumanApprovalProvider:
    async def request_approval(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError
