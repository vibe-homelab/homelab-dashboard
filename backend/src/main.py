"""Homelab GPU Orchestrator - FastAPI Application."""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .api import services_router, system_router, workers_router
from .core.config import get_config
from .launchers.docker_launcher import DockerLauncher
from .launchers.process_launcher import ProcessLauncher
from .orchestrator.gpu_pool import GpuPoolManager
from .orchestrator.request_queue import RequestQueue
from .orchestrator.scheduler import Scheduler
from .orchestrator.service_lifecycle import ServiceLifecycleManager
from .ws import ws_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _build_launchers(config):
    """Build launcher instances based on service config."""
    launchers = {}
    for sid, svc_cfg in config.services.items():
        if svc_cfg.launch.type == "docker":
            launchers[sid] = DockerLauncher(svc_cfg)
        else:
            launchers[sid] = ProcessLauncher(svc_cfg)
    return launchers


async def _broadcast_event(event_type: str, data: dict) -> None:
    """Bridge between Scheduler and WebSocketManager."""
    await ws_manager.broadcast_all(event_type, data)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: start orchestrator, stop on shutdown."""
    config = get_config()
    logger.info("Starting Homelab GPU Orchestrator...")

    # Build components
    gpu_pool = GpuPoolManager(config.gpu_pool)
    request_queue = RequestQueue(
        max_size=config.queue.max_size,
        request_timeout_sec=config.queue.request_timeout_sec,
    )
    launchers = _build_launchers(config)
    lifecycle = ServiceLifecycleManager(config.services, launchers)
    scheduler = Scheduler(
        config=config,
        gpu_pool=gpu_pool,
        request_queue=request_queue,
        lifecycle=lifecycle,
        broadcast=_broadcast_event,
    )

    # Store references on app.state for route handlers
    app.state.config = config
    app.state.gpu_pool = gpu_pool
    app.state.request_queue = request_queue
    app.state.lifecycle = lifecycle
    app.state.scheduler = scheduler

    await scheduler.start()
    logger.info("Orchestrator started - %d services, %d GPUs",
                len(config.services), config.gpu_pool.total_gpus)

    yield

    # Shutdown
    logger.info("Shutting down orchestrator...")
    await scheduler.stop()
    for sid in config.services:
        try:
            await lifecycle.stop_service(sid)
        except Exception:
            pass
    logger.info("Orchestrator shut down")


app = FastAPI(
    title="Homelab GPU Orchestrator",
    description="GPU-aware service orchestration dashboard for self-hosted AI services",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(services_router)
app.include_router(workers_router)
app.include_router(system_router)


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    config = get_config()
    return {
        "name": "Homelab GPU Orchestrator",
        "version": "0.2.0",
        "services_count": len(config.services),
        "gpu_count": config.gpu_pool.total_gpus,
        "endpoints": {
            "health": "/healthz",
            "services": "/api/v1/services",
            "queue": "/api/v1/queue",
            "gpus": "/api/v1/system/gpus",
            "overview": "/api/v1/system/overview",
            "websocket": "/ws",
        },
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    connection_id = await ws_manager.connect(websocket)
    logger.info("WebSocket connected: %s", connection_id)

    # Send initial full state
    try:
        gpu_state = await app.state.gpu_pool.get_state()
        queue_state = await app.state.request_queue.get_state()
        service_states = await app.state.lifecycle.get_all_states()

        await ws_manager.send_to(connection_id, {
            "type": "full_state",
            "timestamp": time.time(),
            "data": {
                "gpus": gpu_state.model_dump(mode="json"),
                "queue": queue_state.model_dump(mode="json"),
                "services": {
                    sid: state.model_dump(mode="json")
                    for sid, state in service_states.items()
                },
            },
        })
    except Exception as e:
        logger.error("Error sending initial state: %s", e)

    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_message(connection_id, data)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", connection_id)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        await ws_manager.disconnect(connection_id)


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run(
        "src.main:app",
        host=config.dashboard.host,
        port=config.dashboard.port,
        reload=True,
    )
