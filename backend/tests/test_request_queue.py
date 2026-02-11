"""Tests for Request Queue."""
import datetime

import pytest

from src.models.queue import QueueEntryStatus
from src.orchestrator.request_queue import RequestQueue


@pytest.fixture
def queue():
    return RequestQueue(max_size=10, request_timeout_sec=5)


@pytest.mark.asyncio
async def test_enqueue(queue):
    entry = await queue.enqueue("llm", {"prompt": "hello"})
    assert entry.service_id == "llm"
    assert entry.status == QueueEntryStatus.PENDING
    assert entry.position == 0


@pytest.mark.asyncio
async def test_fifo_order(queue):
    e1 = await queue.enqueue("llm", {"prompt": "first"})
    e2 = await queue.enqueue("image", {"prompt": "second"})
    e3 = await queue.enqueue("voice_stt", {"audio": "third"})

    state = await queue.get_state()
    assert state.total_pending == 3
    pending = [e for e in state.entries if e.status == QueueEntryStatus.PENDING]
    assert pending[0].id == e1.id
    assert pending[1].id == e2.id
    assert pending[2].id == e3.id


@pytest.mark.asyncio
async def test_dispatch(queue):
    entry = await queue.enqueue("llm", {"prompt": "hello"})
    dispatched = await queue.dispatch(entry.id, [0, 1, 2, 3])
    assert dispatched is not None
    assert dispatched.status == QueueEntryStatus.DISPATCHED
    assert dispatched.gpu_ids == [0, 1, 2, 3]

    state = await queue.get_state()
    assert state.total_pending == 0
    assert state.total_processing == 1


@pytest.mark.asyncio
async def test_mark_completed(queue):
    entry = await queue.enqueue("llm", {"prompt": "hello"})
    await queue.dispatch(entry.id, [0])
    await queue.mark_processing(entry.id)
    completed = await queue.mark_completed(entry.id, {"result": "world"})
    assert completed is not None
    assert completed.status == QueueEntryStatus.COMPLETED
    assert completed.response_payload == {"result": "world"}


@pytest.mark.asyncio
async def test_mark_failed(queue):
    entry = await queue.enqueue("llm", {"prompt": "hello"})
    await queue.dispatch(entry.id, [0])
    failed = await queue.mark_failed(entry.id, "crash")
    assert failed is not None
    assert failed.status == QueueEntryStatus.FAILED
    assert failed.error_message == "crash"


@pytest.mark.asyncio
async def test_cancel(queue):
    entry = await queue.enqueue("llm", {"prompt": "hello"})
    cancelled = await queue.cancel(entry.id)
    assert cancelled is not None
    assert cancelled.status == QueueEntryStatus.CANCELLED

    state = await queue.get_state()
    assert state.total_pending == 0


@pytest.mark.asyncio
async def test_queue_full(queue):
    for i in range(10):
        await queue.enqueue("llm", {"i": i})

    with pytest.raises(ValueError, match="Queue full"):
        await queue.enqueue("llm", {"i": 10})


@pytest.mark.asyncio
async def test_get_entry(queue):
    entry = await queue.enqueue("llm", {"prompt": "hello"})
    found = await queue.get_entry(entry.id)
    assert found is not None
    assert found.id == entry.id

    missing = await queue.get_entry("nonexistent")
    assert missing is None


@pytest.mark.asyncio
async def test_get_pending_for_service(queue):
    await queue.enqueue("llm", {"prompt": "a"})
    await queue.enqueue("image", {"prompt": "b"})
    await queue.enqueue("llm", {"prompt": "c"})

    llm_pending = await queue.get_pending_for_service("llm")
    assert len(llm_pending) == 2
    image_pending = await queue.get_pending_for_service("image")
    assert len(image_pending) == 1


@pytest.mark.asyncio
async def test_expire_timed_out(queue):
    await queue.enqueue("llm", {"prompt": "hello"})
    # Force the entry to be old
    async with queue._lock:
        for e in queue._queue:
            e.created_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=10)

    expired = await queue.expire_timed_out()
    assert len(expired) == 1
    assert expired[0].status == QueueEntryStatus.TIMEOUT


@pytest.mark.asyncio
async def test_event_signaling(queue):
    assert not queue.new_entry_event.is_set()
    await queue.enqueue("llm", {"prompt": "hello"})
    assert queue.new_entry_event.is_set()
    queue.new_entry_event.clear()
    assert not queue.new_entry_event.is_set()
