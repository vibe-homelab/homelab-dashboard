"""Service status API endpoints."""
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import ServiceRegistry

router = APIRouter(prefix="/api/v1/services", tags=["services"])


class GatewayStatus(BaseModel):
    reachable: bool
    latency_ms: float | None = None
    error: str | None = None


class WorkerStatus(BaseModel):
    alias: str
    name: str
    type: str
    status: str = "unknown"
    port: int | None = None
    memory_gb: float | None = None
    uptime_seconds: float | None = None
    idle_seconds: float | None = None


class ServiceStatus(BaseModel):
    service_id: str
    name: str
    description: str
    icon: str
    status: str  # healthy, unhealthy, unknown
    gateway: GatewayStatus
    workers: list[WorkerStatus]


class ServiceListResponse(BaseModel):
    services: list[ServiceStatus]
    timestamp: float


async def check_gateway_health(gateway_url: str, health_endpoint: str) -> GatewayStatus:
    """Check if a gateway is reachable."""
    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{gateway_url}{health_endpoint}")
            latency = (time.time() - start) * 1000
            if response.status_code == 200:
                return GatewayStatus(reachable=True, latency_ms=round(latency, 2))
            return GatewayStatus(
                reachable=False,
                latency_ms=round(latency, 2),
                error=f"HTTP {response.status_code}",
            )
    except httpx.TimeoutException:
        return GatewayStatus(reachable=False, error="Timeout")
    except httpx.ConnectError:
        return GatewayStatus(reachable=False, error="Connection refused")
    except Exception as e:
        return GatewayStatus(reachable=False, error=str(e))


async def get_worker_status(
    worker_manager_url: str, workers_config: list
) -> list[WorkerStatus]:
    """Get worker status from worker manager."""
    workers = []

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{worker_manager_url}/status")
            if response.status_code == 200:
                data = response.json()
                active_workers = data.get("workers", {})

                for worker_cfg in workers_config:
                    alias = worker_cfg.alias
                    if alias in active_workers:
                        w = active_workers[alias]
                        workers.append(
                            WorkerStatus(
                                alias=alias,
                                name=worker_cfg.name,
                                type=worker_cfg.type,
                                status="running",
                                port=w.get("port"),
                                memory_gb=w.get("memory_gb"),
                                uptime_seconds=w.get("uptime_seconds"),
                                idle_seconds=w.get("idle_seconds"),
                            )
                        )
                    else:
                        workers.append(
                            WorkerStatus(
                                alias=alias,
                                name=worker_cfg.name,
                                type=worker_cfg.type,
                                status="stopped",
                            )
                        )
            else:
                # Worker manager not responding properly
                for worker_cfg in workers_config:
                    workers.append(
                        WorkerStatus(
                            alias=worker_cfg.alias,
                            name=worker_cfg.name,
                            type=worker_cfg.type,
                            status="unknown",
                        )
                    )
    except Exception:
        # Worker manager not reachable
        for worker_cfg in workers_config:
            workers.append(
                WorkerStatus(
                    alias=worker_cfg.alias,
                    name=worker_cfg.name,
                    type=worker_cfg.type,
                    status="unknown",
                )
            )

    return workers


@router.get("", response_model=ServiceListResponse)
async def list_services():
    """List all services with their current status."""
    registry = ServiceRegistry()
    services = []

    for service_cfg in registry.list_services():
        # Check gateway health
        gateway_status = await check_gateway_health(
            service_cfg.gateway.url, service_cfg.endpoints.health
        )

        # Get worker status
        workers = await get_worker_status(
            service_cfg.worker_manager.url, service_cfg.workers
        )

        # Determine overall status
        if gateway_status.reachable:
            status = "healthy"
        else:
            status = "unhealthy"

        services.append(
            ServiceStatus(
                service_id=service_cfg.id,
                name=service_cfg.name,
                description=service_cfg.description,
                icon=service_cfg.icon,
                status=status,
                gateway=gateway_status,
                workers=workers,
            )
        )

    return ServiceListResponse(services=services, timestamp=time.time())


@router.get("/{service_id}", response_model=ServiceStatus)
async def get_service(service_id: str):
    """Get detailed status for a specific service."""
    registry = ServiceRegistry()
    service_cfg = registry.get_service(service_id)

    if not service_cfg:
        raise HTTPException(status_code=404, detail=f"Service not found: {service_id}")

    # Check gateway health
    gateway_status = await check_gateway_health(
        service_cfg.gateway.url, service_cfg.endpoints.health
    )

    # Get worker status
    workers = await get_worker_status(
        service_cfg.worker_manager.url, service_cfg.workers
    )

    # Determine overall status
    status = "healthy" if gateway_status.reachable else "unhealthy"

    return ServiceStatus(
        service_id=service_cfg.id,
        name=service_cfg.name,
        description=service_cfg.description,
        icon=service_cfg.icon,
        status=status,
        gateway=gateway_status,
        workers=workers,
    )


@router.get("/{service_id}/status")
async def get_service_system_status(service_id: str) -> dict[str, Any]:
    """Proxy to the service's /v1/system/status endpoint."""
    registry = ServiceRegistry()
    service_cfg = registry.get_service(service_id)

    if not service_cfg:
        raise HTTPException(status_code=404, detail=f"Service not found: {service_id}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{service_cfg.gateway.url}{service_cfg.endpoints.status}"
            )
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")
