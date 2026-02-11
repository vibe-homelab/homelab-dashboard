"""Request queue data models."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class QueueEntryStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class QueueEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    service_id: str
    status: QueueEntryStatus = QueueEntryStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    dispatched_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    request_payload: dict[str, Any] = Field(default_factory=dict)
    response_payload: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    position: Optional[int] = None
    gpu_ids: list[int] = Field(default_factory=list)


class QueueState(BaseModel):
    entries: list[QueueEntry]
    total_pending: int
    total_processing: int
    total_completed: int
