"""Central Scheduler - orchestrates GPU allocation, service lifecycle, and request dispatch."""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

import httpx

from ..core.config import DashboardConfig
from ..models.queue import QueueEntryStatus
from ..models.service import ServiceStatus
from .gpu_pool import GpuPoolManager
from .request_queue import RequestQueue
from .service_lifecycle import ServiceLifecycleManager

logger = logging.getLogger(__name__)

# Type for the WebSocket broadcast callback
EventCallback = Callable[[str, dict], Awaitable[None]]


class Scheduler:
    """Central orchestration loop with 4 async tasks.

    1. dispatch_loop: Watch queue, allocate GPUs, start services, forward requests
    2. idle_loop: Detect idle services and reclaim GPUs
    3. health_loop: Detect crashed services
    4. timeout_loop: Expire timed-out queue entries
    """

    def __init__(
        self,
        config: DashboardConfig,
        gpu_pool: GpuPoolManager,
        request_queue: RequestQueue,
        lifecycle: ServiceLifecycleManager,
        broadcast: EventCallback,
    ) -> None:
        self._config = config
        self._gpu_pool = gpu_pool
        self._queue = request_queue
        self._lifecycle = lifecycle
        self._broadcast = broadcast
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        self._running = True
        self._tasks = [
            asyncio.create_task(self._dispatch_loop(), name="dispatch_loop"),
            asyncio.create_task(self._idle_loop(), name="idle_loop"),
            asyncio.create_task(self._health_loop(), name="health_loop"),
            asyncio.create_task(self._timeout_loop(), name="timeout_loop"),
        ]
        logger.info("Scheduler started with %d loops", len(self._tasks))

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("Scheduler stopped")

    # ------------------------------------------------------------------ #
    #  Dispatch Loop                                                      #
    # ------------------------------------------------------------------ #

    async def _dispatch_loop(self) -> None:
        while self._running:
            try:
                await asyncio.wait_for(
                    self._queue.new_entry_event.wait(),
                    timeout=2.0,
                )
                self._queue.new_entry_event.clear()
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                return

            try:
                await self._try_dispatch_all()
            except Exception:
                logger.exception("Error in dispatch loop")

    async def _try_dispatch_all(self) -> None:
        """Attempt to dispatch as many queued requests as possible."""
        state = await self._queue.get_state()

        for entry in state.entries:
            if entry.status != QueueEntryStatus.PENDING:
                continue

            service_id = entry.service_id
            if service_id not in self._config.services:
                await self._queue.mark_failed(entry.id, f"Unknown service: {service_id}")
                await self._broadcast_queue_update()
                continue

            service_cfg = self._config.services[service_id]
            gpu_req = service_cfg.gpu_requirement
            svc_state = await self._lifecycle.get_state(service_id)

            if svc_state.status == ServiceStatus.HEALTHY:
                # Service already running: forward directly
                await self._dispatch_to_running(entry, service_id)
                continue

            if svc_state.status == ServiceStatus.STARTING:
                # Service starting: skip, will retry on next cycle
                continue

            # Service stopped: try to allocate GPUs
            allocated = await self._gpu_pool.try_allocate(
                service_id=service_id,
                num_gpus=gpu_req.min_gpus,
                exclusive=gpu_req.exclusive,
            )

            if allocated is None:
                logger.debug(
                    "Cannot allocate %d GPUs for %s (exclusive=%s)",
                    gpu_req.min_gpus, service_id, gpu_req.exclusive,
                )
                continue

            await self._dispatch_and_start(entry, service_id, allocated)

    async def _dispatch_to_running(self, entry, service_id: str) -> None:
        """Forward request to an already-running service."""
        svc_state = await self._lifecycle.get_state(service_id)
        dispatched = await self._queue.dispatch(entry.id, svc_state.gpu_ids)
        if not dispatched:
            return

        await self._broadcast_queue_update()
        asyncio.create_task(
            self._forward_request(entry, service_id),
            name=f"forward-{entry.id}",
        )

    async def _dispatch_and_start(self, entry, service_id: str, gpu_ids: list[int]) -> None:
        """Allocate GPUs, start service, forward request."""
        dispatched = await self._queue.dispatch(entry.id, gpu_ids)
        if not dispatched:
            await self._gpu_pool.release(service_id)
            return

        await self._broadcast_gpu_update()
        await self._broadcast_queue_update()

        asyncio.create_task(
            self._start_and_forward(entry, service_id, gpu_ids),
            name=f"start-forward-{entry.id}",
        )

    async def _start_and_forward(self, entry, service_id: str, gpu_ids: list[int]) -> None:
        """Background: start service, wait for health, forward request."""
        try:
            await self._broadcast_service_update(service_id)
            svc_state = await self._lifecycle.start_service(service_id, gpu_ids)
            await self._broadcast_service_update(service_id)
            await self._broadcast_gpu_update()

            if svc_state.status != ServiceStatus.HEALTHY:
                await self._queue.mark_failed(
                    entry.id,
                    f"Service {service_id} failed to start: {svc_state.error_message}",
                )
                await self._gpu_pool.release(service_id)
                await self._broadcast_all_updates()
                return

            await self._forward_request(entry, service_id)

            # After forwarding, try to dispatch more pending requests
            await self._try_dispatch_all()

        except Exception as exc:
            logger.exception("Error in start_and_forward for %s", entry.id)
            await self._queue.mark_failed(entry.id, str(exc))
            await self._gpu_pool.release(service_id)
            await self._broadcast_all_updates()

    async def _forward_request(self, entry, service_id: str) -> None:
        """Forward the actual HTTP request to the running service."""
        service_cfg = self._config.services[service_id]
        port = service_cfg.launch.port

        await self._queue.mark_processing(entry.id)
        await self._lifecycle.record_request_start(service_id)
        await self._broadcast_queue_update()

        try:
            proxy_path = service_cfg.api.proxy_endpoints[0] if service_cfg.api.proxy_endpoints else "/"
            url = f"http://127.0.0.1:{port}{proxy_path}"

            async with httpx.AsyncClient(timeout=600) as client:
                resp = await client.post(url, json=entry.request_payload)
                response_data = resp.json()

            await self._queue.mark_completed(entry.id, response_data)
            logger.info("Request %s completed (service=%s)", entry.id, service_id)

        except Exception as exc:
            logger.exception("Request %s failed", entry.id)
            await self._queue.mark_failed(entry.id, str(exc))

        finally:
            await self._lifecycle.record_request_end(service_id)
            await self._broadcast_queue_update()
            await self._broadcast_service_update(service_id)

    # ------------------------------------------------------------------ #
    #  Idle Reclamation Loop                                              #
    # ------------------------------------------------------------------ #

    async def _idle_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                return

            for service_id in self._config.services:
                try:
                    if not await self._lifecycle.is_idle(service_id):
                        continue

                    # Don't stop if there are pending requests for this service
                    pending = await self._queue.get_pending_for_service(service_id)
                    if pending:
                        continue

                    logger.info("Service %s is idle, stopping and reclaiming GPUs", service_id)
                    await self._lifecycle.stop_service(service_id)
                    released = await self._gpu_pool.release(service_id)

                    await self._broadcast_service_update(service_id)
                    await self._broadcast_gpu_update()

                    if released:
                        logger.info("Reclaimed GPUs %s from %s", released, service_id)
                        self._queue.new_entry_event.set()

                except Exception:
                    logger.exception("Error in idle check for %s", service_id)

    # ------------------------------------------------------------------ #
    #  Health Check Loop                                                  #
    # ------------------------------------------------------------------ #

    async def _health_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(15)
            except asyncio.CancelledError:
                return

            for service_id in self._config.services:
                try:
                    svc_state = await self._lifecycle.get_state(service_id)
                    if svc_state.status not in (ServiceStatus.HEALTHY, ServiceStatus.STARTING):
                        continue

                    launcher = self._lifecycle.get_launcher(service_id)
                    alive = await launcher.is_alive()

                    if not alive:
                        logger.error("Service %s died unexpectedly", service_id)
                        active = await self._queue.get_active_for_service(service_id)
                        for e in active:
                            await self._queue.mark_failed(e.id, f"Service {service_id} crashed")

                        await self._lifecycle.stop_service(service_id)
                        await self._gpu_pool.release(service_id)
                        await self._broadcast_all_updates()
                        self._queue.new_entry_event.set()

                except Exception:
                    logger.exception("Error in health check for %s", service_id)

    # ------------------------------------------------------------------ #
    #  Timeout Loop                                                       #
    # ------------------------------------------------------------------ #

    async def _timeout_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                return

            try:
                expired = await self._queue.expire_timed_out()
                if expired:
                    logger.info("Expired %d timed-out queue entries", len(expired))
                    await self._broadcast_queue_update()
            except Exception:
                logger.exception("Error in timeout loop")

    # ------------------------------------------------------------------ #
    #  Broadcast Helpers                                                  #
    # ------------------------------------------------------------------ #

    async def _broadcast_gpu_update(self) -> None:
        state = await self._gpu_pool.get_state()
        await self._broadcast("gpu_state_changed", state.model_dump(mode="json"))

    async def _broadcast_queue_update(self) -> None:
        state = await self._queue.get_state()
        await self._broadcast("queue_updated", state.model_dump(mode="json"))

    async def _broadcast_service_update(self, service_id: str) -> None:
        state = await self._lifecycle.get_state(service_id)
        await self._broadcast(
            "service_state_changed",
            {"service_id": service_id, **state.model_dump(mode="json")},
        )

    async def _broadcast_all_updates(self) -> None:
        await self._broadcast_gpu_update()
        await self._broadcast_queue_update()
        for sid in self._config.services:
            await self._broadcast_service_update(sid)
