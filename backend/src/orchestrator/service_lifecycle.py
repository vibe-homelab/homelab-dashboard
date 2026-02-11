"""Service Lifecycle Manager - start, stop, health check, idle tracking."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx

from ..core.config import ServiceConfig
from ..launchers.base import ServiceLauncher
from ..models.service import ServiceState, ServiceStatus

logger = logging.getLogger(__name__)


class ServiceLifecycleManager:
    """Manages the lifecycle of all configured services."""

    def __init__(
        self,
        service_configs: dict[str, ServiceConfig],
        launchers: dict[str, ServiceLauncher],
    ) -> None:
        self._configs = service_configs
        self._launchers = launchers
        self._states: dict[str, ServiceState] = {}
        self._lock = asyncio.Lock()

        for sid, cfg in service_configs.items():
            self._states[sid] = ServiceState(
                service_id=sid,
                display_name=cfg.display_name,
            )

    async def get_state(self, service_id: str) -> ServiceState:
        async with self._lock:
            return self._states[service_id].model_copy()

    async def get_all_states(self) -> dict[str, ServiceState]:
        async with self._lock:
            return {
                sid: state.model_copy()
                for sid, state in self._states.items()
            }

    async def start_service(
        self,
        service_id: str,
        gpu_ids: list[int],
    ) -> ServiceState:
        """Start a service on the specified GPUs."""
        async with self._lock:
            state = self._states[service_id]
            if state.status in (ServiceStatus.HEALTHY, ServiceStatus.STARTING):
                return state.model_copy()
            state.status = ServiceStatus.STARTING
            state.gpu_ids = gpu_ids
            state.error_message = None

        config = self._configs[service_id]
        launcher = self._launchers[service_id]

        try:
            result = await launcher.start(
                gpu_ids=gpu_ids,
                port=config.launch.port,
            )

            async with self._lock:
                state = self._states[service_id]
                state.pid = result.get("pid")
                state.container_id = result.get("container_id")
                state.port = config.launch.port
                state.started_at = datetime.utcnow()
                state.last_request_at = datetime.utcnow()

            healthy = await self._wait_for_health(service_id)

            async with self._lock:
                state = self._states[service_id]
                if healthy:
                    state.status = ServiceStatus.HEALTHY
                    logger.info("Service %s is healthy on GPUs %s", service_id, gpu_ids)
                else:
                    state.status = ServiceStatus.ERROR
                    state.error_message = "Startup health check timed out"
                    logger.error("Service %s failed health check", service_id)
                return state.model_copy()

        except Exception as exc:
            async with self._lock:
                state = self._states[service_id]
                state.status = ServiceStatus.ERROR
                state.error_message = str(exc)
            logger.exception("Failed to start service %s", service_id)
            return state.model_copy()

    async def stop_service(self, service_id: str) -> ServiceState:
        """Stop a running service."""
        async with self._lock:
            state = self._states[service_id]
            if state.status == ServiceStatus.STOPPED:
                return state.model_copy()
            state.status = ServiceStatus.STOPPING

        launcher = self._launchers[service_id]
        try:
            await launcher.stop()
        except Exception as exc:
            logger.warning("Error stopping service %s: %s", service_id, exc)

        async with self._lock:
            state = self._states[service_id]
            state.status = ServiceStatus.STOPPED
            state.pid = None
            state.container_id = None
            state.port = None
            state.gpu_ids = []
            state.started_at = None
            state.active_requests = 0
            state.idle_seconds = 0.0
            state.error_message = None
            logger.info("Service %s stopped", service_id)
            return state.model_copy()

    async def record_request_start(self, service_id: str) -> None:
        async with self._lock:
            state = self._states[service_id]
            state.active_requests += 1
            state.last_request_at = datetime.utcnow()

    async def record_request_end(self, service_id: str) -> None:
        async with self._lock:
            state = self._states[service_id]
            state.active_requests = max(0, state.active_requests - 1)
            state.total_requests_served += 1
            state.last_request_at = datetime.utcnow()

    async def is_idle(self, service_id: str) -> bool:
        """Check if service has been idle longer than its configured timeout."""
        async with self._lock:
            state = self._states[service_id]
            if state.status != ServiceStatus.HEALTHY:
                return False
            if state.active_requests > 0:
                return False
            if state.last_request_at is None:
                return True
            config = self._configs[service_id]
            elapsed = (datetime.utcnow() - state.last_request_at).total_seconds()
            state.idle_seconds = elapsed
            return elapsed >= config.idle_timeout_sec

    async def is_running(self, service_id: str) -> bool:
        async with self._lock:
            return self._states[service_id].status in (
                ServiceStatus.HEALTHY,
                ServiceStatus.STARTING,
            )

    def get_launcher(self, service_id: str) -> ServiceLauncher:
        return self._launchers[service_id]

    async def _wait_for_health(self, service_id: str) -> bool:
        """Poll health endpoint until healthy or timeout."""
        config = self._configs[service_id]
        port = config.launch.port
        endpoint = config.health_check.endpoint
        url = f"http://127.0.0.1:{port}{endpoint}"
        timeout_sec = config.health_check.startup_timeout_sec

        deadline = asyncio.get_event_loop().time() + timeout_sec
        while asyncio.get_event_loop().time() < deadline:
            try:
                async with httpx.AsyncClient(timeout=config.health_check.timeout_sec) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        return True
            except Exception:
                pass
            await asyncio.sleep(config.health_check.interval_sec)
        return False
