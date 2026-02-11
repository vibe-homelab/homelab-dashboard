"""Service status API endpoints for GPU Orchestrator."""
import time

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/v1/services", tags=["services"])


@router.get("")
async def list_services(request: Request):
    """List all services with their current state."""
    lifecycle = request.app.state.lifecycle
    config = request.app.state.config
    states = await lifecycle.get_all_states()

    services = []
    for sid, state in states.items():
        svc_cfg = config.services[sid]
        services.append({
            **state.model_dump(mode="json"),
            "description": svc_cfg.description,
            "icon": svc_cfg.icon,
            "gpu_requirement": {
                "min_gpus": svc_cfg.gpu_requirement.min_gpus,
                "max_gpus": svc_cfg.gpu_requirement.max_gpus,
                "exclusive": svc_cfg.gpu_requirement.exclusive,
            },
            "idle_timeout_sec": svc_cfg.idle_timeout_sec,
        })

    return {"services": services, "timestamp": time.time()}


@router.get("/{service_id}")
async def get_service(service_id: str, request: Request):
    """Get detailed status for a specific service."""
    config = request.app.state.config
    lifecycle = request.app.state.lifecycle

    if service_id not in config.services:
        raise HTTPException(status_code=404, detail=f"Service not found: {service_id}")

    state = await lifecycle.get_state(service_id)
    svc_cfg = config.services[service_id]

    return {
        **state.model_dump(mode="json"),
        "description": svc_cfg.description,
        "icon": svc_cfg.icon,
        "gpu_requirement": {
            "min_gpus": svc_cfg.gpu_requirement.min_gpus,
            "max_gpus": svc_cfg.gpu_requirement.max_gpus,
            "exclusive": svc_cfg.gpu_requirement.exclusive,
        },
        "idle_timeout_sec": svc_cfg.idle_timeout_sec,
    }


@router.post("/{service_id}/stop")
async def force_stop_service(service_id: str, request: Request):
    """Force stop a running service and release its GPUs."""
    config = request.app.state.config
    lifecycle = request.app.state.lifecycle
    gpu_pool = request.app.state.gpu_pool

    if service_id not in config.services:
        raise HTTPException(status_code=404, detail=f"Service not found: {service_id}")

    await lifecycle.stop_service(service_id)
    released = await gpu_pool.release(service_id)

    return {
        "success": True,
        "service_id": service_id,
        "released_gpus": released,
    }
