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


def test_concurrent_map_rejects_an_invalid_limit() -> None:
    async def identity(value: int) -> int:
        return value

    with pytest.raises(ValueError, match="must be positive"):
        asyncio.run(map_concurrently([1], identity, limit=0))
