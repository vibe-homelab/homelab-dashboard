"""Worker control API endpoints."""
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import ServiceRegistry

router = APIRouter(prefix="/api/v1/services/{service_id}/workers", tags=["workers"])


class WorkerActionResponse(BaseModel):
    success: bool
    message: str
    worker_alias: str
    action: str
    data: dict[str, Any] | None = None


@router.get("")
async def list_workers(service_id: str):
    """List all workers for a service."""
    registry = ServiceRegistry()
    service_cfg = registry.get_service(service_id)

    if not service_cfg:
        raise HTTPException(status_code=404, detail=f"Service not found: {service_id}")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{service_cfg.worker_manager.url}/status")
            if response.status_code == 200:
                data = response.json()
                active_workers = data.get("workers", {})

                workers = []
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
                return {"workers": workers}
            else:
                raise HTTPException(
                    status_code=503, detail="Worker manager not responding"
                )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Worker manager not reachable")


@router.post("/{alias}/spawn", response_model=WorkerActionResponse)
async def spawn_worker(service_id: str, alias: str):
    """Start/spawn a worker."""
    registry = ServiceRegistry()
    service_cfg = registry.get_service(service_id)

    if not service_cfg:
        raise HTTPException(status_code=404, detail=f"Service not found: {service_id}")

    # Verify worker alias exists in config
    valid_aliases = [w.alias for w in service_cfg.workers]
    if alias not in valid_aliases:
        raise HTTPException(
            status_code=404, detail=f"Worker not found: {alias}"
        )

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{service_cfg.worker_manager.url}/spawn/{alias}"
            )
            if response.status_code == 200:
                data = response.json()
                return WorkerActionResponse(
                    success=True,
                    message=f"Worker '{alias}' spawned successfully",
                    worker_alias=alias,
                    action="spawn",
                    data=data,
                )
            else:
                return WorkerActionResponse(
                    success=False,
                    message=f"Failed to spawn worker: HTTP {response.status_code}",
                    worker_alias=alias,
                    action="spawn",
                    data=response.json() if response.content else None,
                )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Worker spawn timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Worker manager not reachable")


@router.post("/{alias}/stop", response_model=WorkerActionResponse)
async def stop_worker(service_id: str, alias: str):
    """Stop a worker."""
    registry = ServiceRegistry()
    service_cfg = registry.get_service(service_id)

    if not service_cfg:
        raise HTTPException(status_code=404, detail=f"Service not found: {service_id}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{service_cfg.worker_manager.url}/stop/{alias}"
            )
            if response.status_code == 200:
                return WorkerActionResponse(
                    success=True,
                    message=f"Worker '{alias}' stopped successfully",
                    worker_alias=alias,
                    action="stop",
                )
            else:
                return WorkerActionResponse(
                    success=False,
                    message=f"Failed to stop worker: HTTP {response.status_code}",
                    worker_alias=alias,
                    action="stop",
                )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Worker manager not reachable")


@router.post("/{alias}/evict", response_model=WorkerActionResponse)
async def evict_worker(service_id: str, alias: str):
    """Force evict a worker through the gateway."""
    registry = ServiceRegistry()
    service_cfg = registry.get_service(service_id)

    if not service_cfg:
        raise HTTPException(status_code=404, detail=f"Service not found: {service_id}")

    evict_url = service_cfg.endpoints.evict.replace("{alias}", alias)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{service_cfg.gateway.url}{evict_url}")
            if response.status_code == 200:
                return WorkerActionResponse(
                    success=True,
                    message=f"Worker '{alias}' evicted successfully",
                    worker_alias=alias,
                    action="evict",
                )
            else:
                return WorkerActionResponse(
                    success=False,
                    message=f"Failed to evict worker: HTTP {response.status_code}",
                    worker_alias=alias,
                    action="evict",
                )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Gateway not reachable")
