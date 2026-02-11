"""GPU allocation data models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class GpuStatus(str, Enum):
    FREE = "free"
    ALLOCATED = "allocated"
    STARTING = "starting"
    ERROR = "error"


class GpuInfo(BaseModel):
    gpu_id: int
    status: GpuStatus = GpuStatus.FREE
    allocated_to: Optional[str] = None
    allocated_at: Optional[datetime] = None

    def allocate(self, service_id: str) -> None:
        self.status = GpuStatus.ALLOCATED
        self.allocated_to = service_id
        self.allocated_at = datetime.utcnow()

    def release(self) -> None:
        self.status = GpuStatus.FREE
        self.allocated_to = None
        self.allocated_at = None


class GpuPoolState(BaseModel):
    gpus: list[GpuInfo]
    total: int
    free: int
    allocated: int
