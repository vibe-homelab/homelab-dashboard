"""GPU Pool Manager - tracks and allocates GPUs across services."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from ..core.config import GpuPoolConfig
from ..models.gpu import GpuInfo, GpuPoolState, GpuStatus

logger = logging.getLogger(__name__)


class GpuPoolManager:
    """Thread-safe GPU allocation tracker.

    All mutations go through an asyncio.Lock to prevent
    race conditions between the scheduler and API handlers.
    """

    def __init__(self, config: GpuPoolConfig) -> None:
        self._lock = asyncio.Lock()
        self._gpus: dict[int, GpuInfo] = {
            gpu_id: GpuInfo(gpu_id=gpu_id)
            for gpu_id in config.gpu_ids
        }

    @property
    def total(self) -> int:
        return len(self._gpus)

    async def get_state(self) -> GpuPoolState:
        async with self._lock:
            gpus = [g.model_copy() for g in self._gpus.values()]
            free = sum(1 for g in gpus if g.status == GpuStatus.FREE)
            return GpuPoolState(
                gpus=gpus,
                total=len(gpus),
                free=free,
                allocated=len(gpus) - free,
            )

    async def free_gpu_count(self) -> int:
        async with self._lock:
            return sum(1 for g in self._gpus.values() if g.status == GpuStatus.FREE)

    async def try_allocate(
        self,
        service_id: str,
        num_gpus: int,
        exclusive: bool = False,
    ) -> Optional[list[int]]:
        """Attempt to allocate GPUs for a service.

        If exclusive=True, ALL GPUs must be free (for LLM).
        Returns allocated GPU IDs on success, None on failure.
        """
        async with self._lock:
            if exclusive:
                all_free = all(
                    g.status == GpuStatus.FREE for g in self._gpus.values()
                )
                if not all_free:
                    return None
                allocated = sorted(self._gpus.keys())[:num_gpus]
            else:
                # Check no exclusive service is running
                allocated_services = {
                    g.allocated_to for g in self._gpus.values()
                    if g.allocated_to is not None
                }
                # If any service uses all GPUs, nothing else can run
                for sid in allocated_services:
                    count = sum(
                        1 for g in self._gpus.values()
                        if g.allocated_to == sid
                    )
                    if count == len(self._gpus):
                        return None

                free_ids = sorted(
                    gid for gid, g in self._gpus.items()
                    if g.status == GpuStatus.FREE
                )
                if len(free_ids) < num_gpus:
                    return None
                allocated = free_ids[:num_gpus]

            for gid in allocated:
                self._gpus[gid].allocate(service_id)
            logger.info(
                "Allocated GPUs %s to %s (exclusive=%s)",
                allocated, service_id, exclusive,
            )
            return allocated

    async def release(self, service_id: str) -> list[int]:
        """Release all GPUs allocated to a service."""
        async with self._lock:
            released = []
            for gid, gpu in self._gpus.items():
                if gpu.allocated_to == service_id:
                    gpu.release()
                    released.append(gid)
            if released:
                logger.info("Released GPUs %s from %s", released, service_id)
            return released

    async def get_allocation_for(self, service_id: str) -> list[int]:
        async with self._lock:
            return [
                gid for gid, g in self._gpus.items()
                if g.allocated_to == service_id
            ]
