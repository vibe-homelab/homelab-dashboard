"""Service state data models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ServiceStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STOPPING = "stopping"
    ERROR = "error"


class ServiceState(BaseModel):
    service_id: str
    display_name: str
    status: ServiceStatus = ServiceStatus.STOPPED
    gpu_ids: list[int] = Field(default_factory=list)
    port: Optional[int] = None
    pid: Optional[int] = None
    container_id: Optional[str] = None
    started_at: Optional[datetime] = None
    last_request_at: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    active_requests: int = 0
    total_requests_served: int = 0
    error_message: Optional[str] = None
    idle_seconds: float = 0.0
