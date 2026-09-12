"""Bounded asynchronous work scheduling."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import cast

_UNSET = object()


async def map_concurrently[Input, Output](
    items: Sequence[Input],
    function: Callable[[Input], Awaitable[Output]],
    *,
    limit: int,
) -> list[Output]:
    """Map an async function in input order with at most ``limit`` worker tasks."""
    if limit < 1:
        raise ValueError("concurrency limit must be positive")
    if not items:
        return []

    results: list[Output | object] = [_UNSET] * len(items)
    indexed_items = iter(enumerate(items))

    async def consume() -> None:
        # Iterator advancement has no await point, so workers claim each item exactly once.
        for index, item in indexed_items:
            results[index] = await function(item)

    async with asyncio.TaskGroup() as tasks:
        for _ in range(min(limit, len(items))):
            tasks.create_task(consume())

    if any(result is _UNSET for result in results):
        raise RuntimeError("concurrent worker did not produce every result")
    return cast(list[Output], results)
