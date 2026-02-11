"""Abstract base class for service launchers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ServiceLauncher(ABC):
    """Base class for launching and stopping services."""

    @abstractmethod
    async def start(self, gpu_ids: list[int], port: int) -> dict[str, Any]:
        """Start the service. Returns {"pid": int} or {"container_id": str}."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the service."""
        ...

    @abstractmethod
    async def is_alive(self) -> bool:
        """Check if the process/container is still running."""
        ...
