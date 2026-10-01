from __future__ import annotations

import asyncio

import pytest

from opportunities.utils.concurrency import map_concurrently


def test_concurrent_map_bounds_workers_and_preserves_input_order() -> None:
    active = 0
    peak = 0

    async def double(value: int) -> int:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0)
        active -= 1
        return value * 2

    results = asyncio.run(map_concurrently(list(range(20)), double, limit=3))

    assert results == [value * 2 for value in range(20)]
    assert peak == 3


@pytest.mark.parametrize("limit", [-1, 0])
def test_concurrent_map_rejects_an_invalid_limit(limit: int) -> None:
    async def identity(value: int) -> int:
        return value

    with pytest.raises(ValueError, match="must be positive"):
        asyncio.run(map_concurrently([1], identity, limit=limit))


@pytest.mark.parametrize("failed_worker", [False, True])
def test_concurrent_map_cleans_up_running_workers_after_failure_or_cancellation(
    failed_worker: bool,
) -> None:
    started: set[int] = set()
    finished: set[int] = set()

    async def run() -> None:
        # Hold both workers until failure or cancellation; queued items must never start.
        ready, pending = asyncio.Event(), asyncio.Event()

        async def work(value: int) -> int:
            started.add(value)
            if len(started) == 2:
                ready.set()
            try:
                await ready.wait()
                if failed_worker and value == 0:
                    raise ValueError("synthetic worker failure")
                await pending.wait()
                return value
            finally:
                finished.add(value)

        task = asyncio.create_task(map_concurrently(list(range(20)), work, limit=2))
        await ready.wait()
        if failed_worker:
            with pytest.raises(ExceptionGroup) as error:
                await task
            assert len(error.value.exceptions) == 1
            assert isinstance(error.value.exceptions[0], ValueError)
        else:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        assert started == finished == {0, 1}

    asyncio.run(asyncio.wait_for(run(), timeout=5))


def test_concurrent_map_handles_empty_input_and_none_results() -> None:
    called: list[int] = []

    async def record(value: int) -> None:
        called.append(value)

    assert asyncio.run(map_concurrently([], record, limit=2)) == []
    assert called == []
    assert asyncio.run(map_concurrently([1, 2], record, limit=2)) == [None, None]
    assert sorted(called) == [1, 2]
