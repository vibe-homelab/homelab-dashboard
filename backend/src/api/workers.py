"""Queue API endpoints for GPU Orchestrator."""
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/queue", tags=["queue"])


class SubmitRequest(BaseModel):
    service_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class SubmitResponse(BaseModel):
    queue_entry_id: str
    position: int
    service_id: str
    status: str


@router.post("/submit", response_model=SubmitResponse)
async def submit_request(body: SubmitRequest, request: Request):
    """Submit a request to the GPU queue."""
    rq = request.app.state.request_queue
    config = request.app.state.config

    if body.service_id not in config.services:
        raise HTTPException(400, f"Unknown service: {body.service_id}")

    try:
        entry = await rq.enqueue(body.service_id, body.payload)
    except ValueError as exc:
        raise HTTPException(429, str(exc))

    return SubmitResponse(
        queue_entry_id=entry.id,
        position=entry.position or 0,
        service_id=entry.service_id,
        status=entry.status.value,
    )


@router.get("/status/{entry_id}")
async def get_entry_status(entry_id: str, request: Request):
    """Get the status of a specific queue entry."""
    rq = request.app.state.request_queue
    entry = await rq.get_entry(entry_id)
    if not entry:
        raise HTTPException(404, "Queue entry not found")
    return entry.model_dump(mode="json")


@router.delete("/{entry_id}")
async def cancel_entry(entry_id: str, request: Request):
    """Cancel a pending queue entry."""
    rq = request.app.state.request_queue
    entry = await rq.cancel(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found or not in pending state")
    return {"cancelled": True, "entry_id": entry_id}


@router.get("")
async def get_queue(request: Request, include_history: bool = False):
    """Get the full queue state."""
    rq = request.app.state.request_queue
    state = await rq.get_state(include_history=include_history)
    return state.model_dump(mode="json")


class ProxyRequest(BaseModel):
    service_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timeout_sec: int = 600


@router.post("/proxy")
async def proxy_request(body: ProxyRequest, request: Request):
    """Submit a request and wait synchronously for the result."""
    import asyncio

    rq = request.app.state.request_queue
    config = request.app.state.config

    if body.service_id not in config.services:
        raise HTTPException(400, f"Unknown service: {body.service_id}")

    entry = await rq.enqueue(body.service_id, body.payload)

    deadline = asyncio.get_event_loop().time() + body.timeout_sec
    while asyncio.get_event_loop().time() < deadline:
        current = await rq.get_entry(entry.id)
        if current is None:
            raise HTTPException(500, "Entry disappeared")

        if current.status.value in ("completed", "failed", "cancelled", "timeout"):
            return current.model_dump(mode="json")

        await asyncio.sleep(1.0)

    raise HTTPException(504, f"Request {entry.id} timed out after {body.timeout_sec}s")
