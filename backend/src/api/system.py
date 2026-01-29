"""System information API endpoints."""
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import ServiceRegistry

router = APIRouter(prefix="/api/v1/system", tags=["system"])


class MemoryStatus(BaseModel):
    total_gb: float
    available_gb: float
    used_gb: float
    used_percent: float


class WorkerManagerStatus(BaseModel):
    service_id: str
    reachable: bool
    workers_count: int
    memory: MemoryStatus | None = None
    error: str | None = None


class SystemOverview(BaseModel):
    timestamp: float
    services_count: int
    healthy_services: int
    unhealthy_services: int
    total_workers: int
    running_workers: int
    worker_managers: list[WorkerManagerStatus]


async def get_worker_manager_status(
    service_id: str, worker_manager_url: str
) -> WorkerManagerStatus:
    """Get status from a worker manager."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{worker_manager_url}/status")
            if response.status_code == 200:
                data = response.json()
                workers = data.get("workers", {})

                # Extract memory info if available
                memory = None
                if "memory" in data:
                    mem = data["memory"]
                    memory = MemoryStatus(
                        total_gb=mem.get("total_gb", 0),
                        available_gb=mem.get("available_gb", 0),
                        used_gb=mem.get("used_gb", 0),
                        used_percent=mem.get("used_percent", 0),
                    )

                return WorkerManagerStatus(
                    service_id=service_id,
                    reachable=True,
                    workers_count=len(workers),
                    memory=memory,
                )
            return WorkerManagerStatus(
                service_id=service_id,
                reachable=False,
                workers_count=0,
                error=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return WorkerManagerStatus(
            service_id=service_id,
            reachable=False,
            workers_count=0,
            error=str(e),
        )


@router.get("/overview", response_model=SystemOverview)
async def get_system_overview():
    """Get overall system status."""
    registry = ServiceRegistry()

    healthy_services = 0
    unhealthy_services = 0
    total_workers = 0
    running_workers = 0
    worker_managers: list[WorkerManagerStatus] = []

    # Track unique worker manager URLs to avoid duplicates
    seen_wm_urls: set[str] = set()

    for service_cfg in registry.list_services():
        # Check gateway health
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{service_cfg.gateway.url}{service_cfg.endpoints.health}"
                )
                if response.status_code == 200:
                    healthy_services += 1
                else:
                    unhealthy_services += 1
        except Exception:
            unhealthy_services += 1

        # Count workers
        total_workers += len(service_cfg.workers)

        # Get worker manager status (deduplicated)
        wm_url = service_cfg.worker_manager.url
        if wm_url not in seen_wm_urls:
            seen_wm_urls.add(wm_url)
            wm_status = await get_worker_manager_status(service_cfg.id, wm_url)
            worker_managers.append(wm_status)
            running_workers += wm_status.workers_count

    return SystemOverview(
        timestamp=time.time(),
        services_count=len(registry.list_services()),
        healthy_services=healthy_services,
        unhealthy_services=unhealthy_services,
        total_workers=total_workers,
        running_workers=running_workers,
        worker_managers=worker_managers,
    )


@router.get("/memory")
async def get_system_memory() -> dict[str, Any]:
    """Get system memory information from all worker managers."""
    registry = ServiceRegistry()

    seen_wm_urls: set[str] = set()
    memory_info: list[dict[str, Any]] = []

    for service_cfg in registry.list_services():
        wm_url = service_cfg.worker_manager.url
        if wm_url not in seen_wm_urls:
            seen_wm_urls.add(wm_url)
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{wm_url}/status")
                    if response.status_code == 200:
                        data = response.json()
                        if "memory" in data:
                            memory_info.append(
                                {
                                    "source": wm_url,
                                    "service_id": service_cfg.id,
                                    **data["memory"],
                                }
                            )
            except Exception:
                pass

    return {
        "timestamp": time.time(),
        "memory_sources": memory_info,
    }


@router.post("/worker-manager/{service_id}/stop-all")
async def stop_all_workers(service_id: str):
    """Stop all workers for a service via worker manager."""
    registry = ServiceRegistry()
    service_cfg = registry.get_service(service_id)

    if not service_cfg:
        raise HTTPException(status_code=404, detail=f"Service not found: {service_id}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{service_cfg.worker_manager.url}/stop-all"
            )
            if response.status_code == 200:
                return {"success": True, "message": "All workers stopped"}
            else:
                return {
                    "success": False,
                    "message": f"Failed: HTTP {response.status_code}",
                }
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Worker manager not reachable")
