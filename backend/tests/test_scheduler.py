"""Tests for the Scheduler with mocked launchers."""
import asyncio
import datetime
from unittest.mock import AsyncMock

import pytest

from src.core.config import (
    ApiConfig,
    DashboardConfig,
    DashboardSettings,
    GpuPoolConfig,
    GpuRequirement,
    HealthCheckConfig,
    LaunchConfig,
    PollingConfig,
    QueueConfig,
    ServiceConfig,
    WebSocketConfig,
)
from src.launchers.base import ServiceLauncher
from src.models.queue import QueueEntryStatus
from src.models.service import ServiceStatus
from src.orchestrator.gpu_pool import GpuPoolManager
from src.orchestrator.request_queue import RequestQueue
from src.orchestrator.service_lifecycle import ServiceLifecycleManager


class MockLauncher(ServiceLauncher):
    """Mock launcher that pretends to start/stop instantly."""

    def __init__(self):
        self.started = False

    async def start(self, gpu_ids: list[int], port: int) -> dict:
        self.started = True
        return {"pid": 12345}

    async def stop(self) -> None:
        self.started = False

    async def is_alive(self) -> bool:
        return self.started


def _make_config(gpu_ids=None):
    if gpu_ids is None:
        gpu_ids = [0, 1, 2, 3]

    svc_configs = {
        "voice_stt": ServiceConfig(
            id="voice_stt",
            display_name="Voice STT",
            gpu_requirement=GpuRequirement(min_gpus=1, max_gpus=1, exclusive=False),
            launch=LaunchConfig(type="process", port=9001),
            health_check=HealthCheckConfig(startup_timeout_sec=2),
            idle_timeout_sec=2,
            api=ApiConfig(proxy_endpoints=["/v1/test"]),
        ),
        "llm": ServiceConfig(
            id="llm",
            display_name="LLM",
            gpu_requirement=GpuRequirement(min_gpus=4, max_gpus=4, exclusive=True),
            launch=LaunchConfig(type="process", port=9000),
            health_check=HealthCheckConfig(startup_timeout_sec=2),
            idle_timeout_sec=2,
            api=ApiConfig(proxy_endpoints=["/v1/test"]),
        ),
    }

    return DashboardConfig(
        dashboard=DashboardSettings(),
        gpu_pool=GpuPoolConfig(total_gpus=len(gpu_ids), gpu_ids=gpu_ids),
        services=svc_configs,
        queue=QueueConfig(max_size=50, request_timeout_sec=30),
        polling=PollingConfig(),
        websocket=WebSocketConfig(),
    )


@pytest.fixture
def config():
    return _make_config()


@pytest.fixture
def gpu_pool(config):
    return GpuPoolManager(config.gpu_pool)


@pytest.fixture
def request_queue(config):
    return RequestQueue(
        max_size=config.queue.max_size,
        request_timeout_sec=config.queue.request_timeout_sec,
    )


@pytest.fixture
def mock_launchers(config):
    return {sid: MockLauncher() for sid in config.services}


@pytest.fixture
def lifecycle(config, mock_launchers):
    return ServiceLifecycleManager(config.services, mock_launchers)


@pytest.mark.asyncio
async def test_gpu_pool_allocate_and_release(gpu_pool):
    result = await gpu_pool.try_allocate("voice_stt", 1, exclusive=False)
    assert result == [0]
    state = await gpu_pool.get_state()
    assert state.free == 3
    released = await gpu_pool.release("voice_stt")
    assert released == [0]
    state = await gpu_pool.get_state()
    assert state.free == 4


@pytest.mark.asyncio
async def test_exclusive_blocks_non_exclusive(gpu_pool):
    await gpu_pool.try_allocate("llm", 4, exclusive=True)
    result = await gpu_pool.try_allocate("voice_stt", 1, exclusive=False)
    assert result is None


@pytest.mark.asyncio
async def test_non_exclusive_blocks_exclusive(gpu_pool):
    await gpu_pool.try_allocate("voice_stt", 1, exclusive=False)
    result = await gpu_pool.try_allocate("llm", 4, exclusive=True)
    assert result is None


@pytest.mark.asyncio
async def test_lifecycle_start_stop(lifecycle, mock_launchers):
    lifecycle._wait_for_health = AsyncMock(return_value=True)

    state = await lifecycle.start_service("voice_stt", [0])
    assert state.status == ServiceStatus.HEALTHY
    assert state.gpu_ids == [0]
    assert mock_launchers["voice_stt"].started

    state = await lifecycle.stop_service("voice_stt")
    assert state.status == ServiceStatus.STOPPED
    assert not mock_launchers["voice_stt"].started


@pytest.mark.asyncio
async def test_lifecycle_idle_detection(lifecycle, mock_launchers):
    lifecycle._wait_for_health = AsyncMock(return_value=True)
    await lifecycle.start_service("voice_stt", [0])

    # Just started, should not be idle
    is_idle = await lifecycle.is_idle("voice_stt")
    assert not is_idle

    # Force last_request_at to be old
    async with lifecycle._lock:
        lifecycle._states["voice_stt"].last_request_at = (
            datetime.datetime.utcnow() - datetime.timedelta(seconds=10)
        )

    is_idle = await lifecycle.is_idle("voice_stt")
    assert is_idle


@pytest.mark.asyncio
async def test_queue_enqueue_dispatch_complete(request_queue):
    entry = await request_queue.enqueue("voice_stt", {"audio": "test"})
    assert entry.status == QueueEntryStatus.PENDING

    dispatched = await request_queue.dispatch(entry.id, [0])
    assert dispatched.status == QueueEntryStatus.DISPATCHED

    await request_queue.mark_processing(entry.id)
    completed = await request_queue.mark_completed(entry.id, {"text": "result"})
    assert completed.status == QueueEntryStatus.COMPLETED
