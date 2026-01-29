"""Homelab Dashboard - FastAPI Application."""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .api import services_router, workers_router, system_router
from .core import get_config
from .services.health_checker import health_checker
from .ws import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("Starting Homelab Dashboard...")
    await health_checker.start()
    print("Health checker started")

    yield

    # Shutdown
    print("Shutting down...")
    await health_checker.stop()
    print("Health checker stopped")


app = FastAPI(
    title="Homelab Dashboard",
    description="Monitoring and management dashboard for vibe-homelab services",
    version="0.1.0",
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
        "name": "Homelab Dashboard API",
        "version": "0.1.0",
        "services_count": len(config.services),
        "endpoints": {
            "health": "/healthz",
            "services": "/api/v1/services",
            "system": "/api/v1/system/overview",
            "websocket": "/ws",
        },
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    connection_id = await ws_manager.connect(websocket)
    print(f"WebSocket connected: {connection_id}")

    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.handle_message(connection_id, data)
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
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
