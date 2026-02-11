"""Tests for GPU Pool Manager."""
import pytest

from src.core.config import GpuPoolConfig
from src.models.gpu import GpuStatus
from src.orchestrator.gpu_pool import GpuPoolManager


@pytest.fixture
def pool():
    config = GpuPoolConfig(total_gpus=4, gpu_ids=[0, 1, 2, 3])
    return GpuPoolManager(config)


@pytest.mark.asyncio
async def test_initial_state(pool):
    state = await pool.get_state()
    assert state.total == 4
    assert state.free == 4
    assert state.allocated == 0
    assert all(g.status == GpuStatus.FREE for g in state.gpus)


@pytest.mark.asyncio
async def test_allocate_non_exclusive(pool):
    result = await pool.try_allocate("image", 2, exclusive=False)
    assert result == [0, 1]
    state = await pool.get_state()
    assert state.free == 2
    assert state.allocated == 2


@pytest.mark.asyncio
async def test_allocate_exclusive_all_free(pool):
    result = await pool.try_allocate("llm", 4, exclusive=True)
    assert result == [0, 1, 2, 3]
    state = await pool.get_state()
    assert state.free == 0
    assert state.allocated == 4


@pytest.mark.asyncio
async def test_allocate_exclusive_fails_when_busy(pool):
    await pool.try_allocate("voice_stt", 1, exclusive=False)
    result = await pool.try_allocate("llm", 4, exclusive=True)
    assert result is None


@pytest.mark.asyncio
async def test_allocate_fails_insufficient_gpus(pool):
    await pool.try_allocate("image", 3, exclusive=False)
    result = await pool.try_allocate("voice_stt", 2, exclusive=False)
    assert result is None


@pytest.mark.asyncio
async def test_release(pool):
    await pool.try_allocate("image", 2, exclusive=False)
    released = await pool.release("image")
    assert released == [0, 1]
    state = await pool.get_state()
    assert state.free == 4


@pytest.mark.asyncio
async def test_multiple_services_coexist(pool):
    result1 = await pool.try_allocate("voice_stt", 1, exclusive=False)
    result2 = await pool.try_allocate("voice_tts", 1, exclusive=False)
    result3 = await pool.try_allocate("image", 2, exclusive=False)
    assert result1 == [0]
    assert result2 == [1]
    assert result3 == [2, 3]
    state = await pool.get_state()
    assert state.free == 0


@pytest.mark.asyncio
async def test_non_exclusive_blocked_by_exclusive_service(pool):
    await pool.try_allocate("llm", 4, exclusive=True)
    result = await pool.try_allocate("voice_stt", 1, exclusive=False)
    assert result is None


@pytest.mark.asyncio
async def test_release_nonexistent_service(pool):
    released = await pool.release("nonexistent")
    assert released == []


@pytest.mark.asyncio
async def test_get_allocation_for(pool):
    await pool.try_allocate("image", 2, exclusive=False)
    alloc = await pool.get_allocation_for("image")
    assert alloc == [0, 1]
    alloc_none = await pool.get_allocation_for("llm")
    assert alloc_none == []
