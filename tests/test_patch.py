from __future__ import annotations

import asyncio

import pytest


def test_patch_adds_to_process_to_asyncio_module():
    # Remove cached attribute if present from a prior test run
    if hasattr(asyncio, "to_process"):
        delattr(asyncio, "to_process")
    if hasattr(asyncio.BaseEventLoop, "to_process"):
        delattr(asyncio.BaseEventLoop, "to_process")

    import async_patcher.patch as patch_module

    patch_module._patched = False

    from async_patcher.patch import patch

    patch()

    assert hasattr(asyncio, "to_process"), "asyncio.to_process not found after patch()"
    assert callable(asyncio.to_process)


def test_patch_adds_to_process_to_base_event_loop():
    from async_patcher.patch import patch

    patch()

    assert hasattr(asyncio.BaseEventLoop, "to_process"), (
        "asyncio.BaseEventLoop.to_process not found after patch()"
    )
    assert callable(asyncio.BaseEventLoop.to_process)


def test_patch_is_idempotent():
    from async_patcher.patch import patch

    patch()
    first_fn = asyncio.to_process
    patch()
    second_fn = asyncio.to_process

    assert first_fn is second_fn, "patch() changed asyncio.to_process on second call"


def add_numbers(x, y):
    return x + y


@pytest.mark.asyncio
async def test_asyncio_to_process_end_to_end():
    """asyncio.to_process available after import; awaiting it returns the result."""
    import async_patcher  # noqa: F401 — triggers auto-patch

    task = asyncio.to_process(add_numbers, 3, 4)

    from async_patcher import ProcessTask

    assert isinstance(task, ProcessTask)

    result = await task
    assert result == 7
    assert task.status == "done"
    assert task.pid is not None


@pytest.mark.asyncio
async def test_loop_to_process_end_to_end():
    """loop.to_process available after import; awaiting it returns the result."""
    import async_patcher  # noqa: F401 — triggers auto-patch

    loop = asyncio.get_event_loop()
    task = loop.to_process(add_numbers, 10, 20)

    from async_patcher import ProcessTask

    assert isinstance(task, ProcessTask)

    result = await task
    assert result == 30
    assert task.status == "done"


@pytest.mark.asyncio
async def test_to_process_with_kwargs():
    """to_process correctly passes keyword arguments to the callable."""
    import async_patcher  # noqa: F401

    task = asyncio.to_process(add_numbers, x=100, y=200)
    result = await task
    assert result == 300


def test_to_process_outside_loop_raises():
    """asyncio.to_process raises RuntimeError outside a running loop."""
    import async_patcher  # noqa: F401

    with pytest.raises(RuntimeError, match="requires a running event loop"):
        asyncio.to_process(add_numbers, 1, 2)
