"""Background health checker that polls services and broadcasts updates."""
import asyncio
import time
from typing import Any

import httpx

from ..core import ServiceRegistry, get_config
from ..ws import ws_manager


class HealthChecker:
    """Background task that polls service health and broadcasts updates."""

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self.registry = ServiceRegistry()
        self.config = get_config()

    async def start(self):
        """Start the background polling task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self):
        """Stop the background polling task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _poll_loop(self):
        """Main polling loop."""
        while self._running:
            try:
                await self._poll_all_services()
            except Exception as e:
                print(f"Error in health check loop: {e}")

            await asyncio.sleep(self.config.polling.status_interval_seconds)

    async def _poll_all_services(self):
        """Poll all services and broadcast updates."""
        for service_cfg in self.registry.list_services():
            try:
                status = await self._check_service(service_cfg)
                await ws_manager.broadcast("services", status)
            except Exception as e:
                print(f"Error checking service {service_cfg.id}: {e}")

    async def _check_service(self, service_cfg) -> dict[str, Any]:
        """Check a single service's health and worker status."""
        gateway_status = await self._check_gateway(service_cfg)
        workers = await self._get_workers(service_cfg)

        overall_status = "healthy" if gateway_status["reachable"] else "unhealthy"

        return {
            "service_id": service_cfg.id,
            "name": service_cfg.name,
            "status": overall_status,
            "gateway": gateway_status,
            "workers": workers,
            "timestamp": time.time(),
        }

    async def _check_gateway(self, service_cfg) -> dict[str, Any]:
        """Check gateway health."""
        try:
            start = time.time()
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{service_cfg.gateway.url}{service_cfg.endpoints.health}"
                )
                latency = (time.time() - start) * 1000
                if response.status_code == 200:
                    return {"reachable": True, "latency_ms": round(latency, 2)}
                return {
                    "reachable": False,
                    "latency_ms": round(latency, 2),
                    "error": f"HTTP {response.status_code}",
                }
        except httpx.TimeoutException:
            return {"reachable": False, "error": "Timeout"}
        except httpx.ConnectError:
            return {"reachable": False, "error": "Connection refused"}
        except Exception as e:
            return {"reachable": False, "error": str(e)}

    async def _get_workers(self, service_cfg) -> list[dict[str, Any]]:
        """Get worker status from worker manager."""
        workers = []
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{service_cfg.worker_manager.url}/status"
                )
                if response.status_code == 200:
                    data = response.json()
                    active_workers = data.get("workers", {})

                    for worker_cfg in service_cfg.workers:
                        alias = worker_cfg.alias
                        if alias in active_workers:
                            w = active_workers[alias]
                            workers.append(
                                {
                                    "alias": alias,
                                    "name": worker_cfg.name,
                                    "type": worker_cfg.type,
                                    "status": "running",
                                    "port": w.get("port"),
                                    "memory_gb": w.get("memory_gb"),
                                    "uptime_seconds": w.get("uptime_seconds"),
                                    "idle_seconds": w.get("idle_seconds"),
                                }
                            )
                        else:
                            workers.append(
                                {
                                    "alias": alias,
                                    "name": worker_cfg.name,
                                    "type": worker_cfg.type,
                                    "status": "stopped",
                                }
                            )
                else:
                    workers = self._unknown_workers(service_cfg)
        except Exception:
            workers = self._unknown_workers(service_cfg)

        return workers

    def _unknown_workers(self, service_cfg) -> list[dict[str, Any]]:
        """Return workers with unknown status."""
        return [
            {
                "alias": w.alias,
                "name": w.name,
                "type": w.type,
                "status": "unknown",
            }
            for w in service_cfg.workers
        ]


# Global health checker instance
health_checker = HealthChecker()
