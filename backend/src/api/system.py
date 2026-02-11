"""System overview API endpoints for GPU Orchestrator."""
import time

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/overview")
async def get_system_overview(request: Request):
    """Get aggregated system overview."""
    gpu_pool = request.app.state.gpu_pool
    queue = request.app.state.request_queue
    lifecycle = request.app.state.lifecycle

    gpu_state = await gpu_pool.get_state()
    queue_state = await queue.get_state()
    all_services = await lifecycle.get_all_states()

    running_count = sum(
        1 for s in all_services.values()
        if s.status.value == "healthy"
    )
    stopped_count = sum(
        1 for s in all_services.values()
        if s.status.value == "stopped"
    )

    return {
        "timestamp": time.time(),
        "gpu": {
            "total": gpu_state.total,
            "free": gpu_state.free,
            "allocated": gpu_state.allocated,
        },
        "queue": {
            "pending": queue_state.total_pending,
            "processing": queue_state.total_processing,
            "completed": queue_state.total_completed,
        },
        "services": {
            "total": len(all_services),
            "running": running_count,
            "stopped": stopped_count,
        },
    }


@router.get("/gpus")
async def get_gpu_state(request: Request):
    """Get detailed GPU allocation state."""
    gpu_pool = request.app.state.gpu_pool
    state = await gpu_pool.get_state()
    return state.model_dump(mode="json")
