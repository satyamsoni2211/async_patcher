"""Tests for on_start, on_done, on_error callbacks on to_process()."""

from __future__ import annotations

import asyncio

import pytest


def _double(x):
    return x * 2


def _boom():
    raise ValueError("nope")


@pytest.mark.asyncio
async def test_on_start_called_with_task():
    import async_patcher.patch  # noqa: F401

    seen = []

    def on_start(task):
        seen.append(("start", task))

    task = asyncio.to_process(_double, 5, on_start=on_start)
    await task
    assert len(seen) == 1
    assert seen[0][0] == "start"
    assert seen[0][1] is task


@pytest.mark.asyncio
async def test_on_done_called_with_task():
    import async_patcher.patch  # noqa: F401

    seen = []

    def on_done(task):
        seen.append(("done", task))

    task = asyncio.to_process(_double, 7, on_done=on_done)
    await task
    assert seen == [("done", task)]


@pytest.mark.asyncio
async def test_on_error_called_with_task():
    import async_patcher.patch  # noqa: F401

    seen = []

    def on_error(task):
        seen.append(("error", task))

    task = asyncio.to_process(_boom, on_error=on_error)
    with pytest.raises(ValueError):
        await task
    assert len(seen) == 1
    assert seen[0][0] == "error"
    assert seen[0][1] is task
    assert seen[0][1].status.value == "failed"


@pytest.mark.asyncio
async def test_all_callbacks_called_in_order_on_success():
    import async_patcher.patch  # noqa: F401

    order = []

    def on_start(task):
        order.append("start")

    def on_done(task):
        order.append("done")

    def on_error(task):
        order.append("error")

    task = asyncio.to_process(_double, 3, on_start=on_start, on_done=on_done, on_error=on_error)
    await task
    assert order == ["start", "done"]


@pytest.mark.asyncio
async def test_all_callbacks_called_in_order_on_failure():
    import async_patcher.patch  # noqa: F401

    order = []

    def on_start(task):
        order.append("start")

    def on_done(task):
        order.append("done")

    def on_error(task):
        order.append("error")

    task = asyncio.to_process(_boom, on_start=on_start, on_done=on_done, on_error=on_error)
    with pytest.raises(ValueError):
        await task
    assert order == ["start", "error"]


@pytest.mark.asyncio
async def test_callbacks_default_to_none():
    """No callbacks passed — task still works."""
    import async_patcher.patch  # noqa: F401

    task = asyncio.to_process(_double, 4)
    result = await task
    assert result == 8


@pytest.mark.asyncio
async def test_callback_receives_task_with_duration_set():
    import async_patcher.patch  # noqa: F401

    captured = {}

    def on_done(task):
        captured["duration"] = task.duration
        captured["status"] = task.status

    task = asyncio.to_process(_double, 4, on_done=on_done)
    await task
    assert captured["duration"] is not None
    assert captured["status"].value == "done"
