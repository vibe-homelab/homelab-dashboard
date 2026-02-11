"""FIFO Request Queue with async signaling."""
from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Optional

from ..models.queue import QueueEntry, QueueEntryStatus, QueueState

logger = logging.getLogger(__name__)


class RequestQueue:
    """FIFO request queue with async event signaling for the scheduler."""

    def __init__(self, max_size: int = 100, request_timeout_sec: int = 1800) -> None:
        self._lock = asyncio.Lock()
        self._queue: deque[QueueEntry] = deque()
        self._active: dict[str, QueueEntry] = {}
        self._history: deque[QueueEntry] = deque(maxlen=200)
        self._max_size = max_size
        self._request_timeout = timedelta(seconds=request_timeout_sec)
        self._new_entry_event = asyncio.Event()

    @property
    def new_entry_event(self) -> asyncio.Event:
        return self._new_entry_event

    async def enqueue(
        self,
        service_id: str,
        request_payload: dict[str, Any],
    ) -> QueueEntry:
        async with self._lock:
            if len(self._queue) >= self._max_size:
                raise ValueError(f"Queue full ({self._max_size} entries)")

            entry = QueueEntry(
                service_id=service_id,
                request_payload=request_payload,
            )
            self._queue.append(entry)
            self._recompute_positions()

        self._new_entry_event.set()
        logger.info(
            "Enqueued %s for service=%s (queue size=%d)",
            entry.id, service_id, len(self._queue),
        )
        return entry

    async def peek_next(self) -> Optional[QueueEntry]:
        async with self._lock:
            return self._queue[0] if self._queue else None

    async def dispatch(self, entry_id: str, gpu_ids: list[int]) -> Optional[QueueEntry]:
        """Mark entry as dispatched and move to active tracking."""
        async with self._lock:
            for entry in self._queue:
                if entry.id == entry_id:
                    entry.status = QueueEntryStatus.DISPATCHED
                    entry.dispatched_at = datetime.utcnow()
                    entry.gpu_ids = gpu_ids
                    self._queue.remove(entry)
                    self._active[entry.id] = entry
                    self._recompute_positions()
                    return entry
            return None

    async def mark_processing(self, entry_id: str) -> Optional[QueueEntry]:
        async with self._lock:
            entry = self._active.get(entry_id)
            if entry:
                entry.status = QueueEntryStatus.PROCESSING
            return entry

    async def mark_completed(
        self,
        entry_id: str,
        response_payload: Optional[dict] = None,
    ) -> Optional[QueueEntry]:
        async with self._lock:
            entry = self._active.pop(entry_id, None)
            if entry:
                entry.status = QueueEntryStatus.COMPLETED
                entry.completed_at = datetime.utcnow()
                entry.response_payload = response_payload
                self._history.append(entry)
            return entry

    async def mark_failed(
        self,
        entry_id: str,
        error_message: str,
    ) -> Optional[QueueEntry]:
        async with self._lock:
            entry = self._active.pop(entry_id, None)
            if not entry:
                for e in list(self._queue):
                    if e.id == entry_id:
                        entry = e
                        self._queue.remove(e)
                        break
            if entry:
                entry.status = QueueEntryStatus.FAILED
                entry.completed_at = datetime.utcnow()
                entry.error_message = error_message
                self._history.append(entry)
                self._recompute_positions()
            return entry

    async def cancel(self, entry_id: str) -> Optional[QueueEntry]:
        async with self._lock:
            for entry in list(self._queue):
                if entry.id == entry_id:
                    entry.status = QueueEntryStatus.CANCELLED
                    entry.completed_at = datetime.utcnow()
                    self._queue.remove(entry)
                    self._history.append(entry)
                    self._recompute_positions()
                    return entry
            return None

    async def get_pending_for_service(self, service_id: str) -> list[QueueEntry]:
        async with self._lock:
            return [e for e in self._queue if e.service_id == service_id]

    async def get_active_for_service(self, service_id: str) -> list[QueueEntry]:
        async with self._lock:
            return [
                e for e in self._active.values()
                if e.service_id == service_id
            ]

    async def get_state(self, include_history: bool = False) -> QueueState:
        async with self._lock:
            entries = list(self._queue) + list(self._active.values())
            if include_history:
                entries += list(self._history)
            return QueueState(
                entries=[e.model_copy() for e in entries],
                total_pending=len(self._queue),
                total_processing=len(self._active),
                total_completed=sum(
                    1 for e in self._history
                    if e.status == QueueEntryStatus.COMPLETED
                ),
            )

    async def get_entry(self, entry_id: str) -> Optional[QueueEntry]:
        async with self._lock:
            for e in self._queue:
                if e.id == entry_id:
                    return e.model_copy()
            if entry_id in self._active:
                return self._active[entry_id].model_copy()
            for e in self._history:
                if e.id == entry_id:
                    return e.model_copy()
            return None

    async def expire_timed_out(self) -> list[QueueEntry]:
        expired = []
        now = datetime.utcnow()
        async with self._lock:
            to_remove = []
            for entry in self._queue:
                if now - entry.created_at > self._request_timeout:
                    entry.status = QueueEntryStatus.TIMEOUT
                    entry.completed_at = now
                    to_remove.append(entry)
            for entry in to_remove:
                self._queue.remove(entry)
                self._history.append(entry)
                expired.append(entry)
            if expired:
                self._recompute_positions()
        return expired

    def _recompute_positions(self) -> None:
        for i, entry in enumerate(self._queue):
            entry.position = i
