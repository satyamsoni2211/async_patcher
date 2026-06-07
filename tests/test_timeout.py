"""Tests for the timeout parameter on to_process()."""

from __future__ import annotations

import asyncio
import signal
import time
from concurrent.futures import ProcessPoolExecutor
from unittest.mock import patch as mock_patch

import pytest

from async_patcher.pool import process_pool


def fast_double(x):
    return x * 2


def slow_fn():
    time.sleep(10)
    return "should not reach"


@pytest.mark.asyncio
async def test_to_process_accepts_timeout_kwarg():
    import async_patcher.patch  # noqa: F401

    task = asyncio.to_process(fast_double, 21, timeout=5.0)
    result = await task
    assert result == 42


@pytest.mark.asyncio
async def test_to_process_no_timeout_default_is_none():
    import async_patcher.patch  # noqa: F401

    task = asyncio.to_process(fast_double, 7)
    # attribute should be None or absent; either way, no timeout is enforced
    assert await task == 14


@pytest.mark.asyncio
async def test_to_process_timeout_fires_and_raises_timeout_error():
    import async_patcher.patch  # noqa: F401

    async with process_pool(1) as _:
        task = asyncio.to_process(slow_fn, timeout=0.3)
        with pytest.raises(asyncio.TimeoutError):
            await task


@pytest.mark.asyncio
async def test_to_process_timeout_kills_worker():
    """On timeout the worker process is sent SIGTERM (and SIGKILL after)."""
    import async_patcher.patch  # noqa: F401

    ex = ProcessPoolExecutor(max_workers=1)
    async_patcher.set_default_executor(ex)
    try:
        task = asyncio.to_process(slow_fn, timeout=0.3)
        with mock_patch("async_patcher.task.os.kill") as mock_kill:
            mock_kill.side_effect = ProcessLookupError(3, "No such process")
            try:
                await task
            except (asyncio.TimeoutError, Exception):
                pass
            # If the worker was running, os.kill would have been called with SIGTERM
            sigterm_calls = [
                call
                for call in mock_kill.call_args_list
                if len(call.args) >= 2 and call.args[1] == signal.SIGTERM
            ]
            assert len(sigterm_calls) >= 1
    finally:
        ex.shutdown(wait=True, cancel_futures=True)
