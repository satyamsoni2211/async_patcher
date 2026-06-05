import asyncio
import os
import pytest
from async_patcher.task import _worker_wrapper, ProcessTask
import functools


def test_worker_wrapper_returns_pid_and_result():
    partial = functools.partial(lambda x: x * 2, 5)
    pid, result = _worker_wrapper(partial)
    assert isinstance(pid, int)
    assert pid > 0
    assert result == 10


def test_worker_wrapper_propagates_exception():
    def boom():
        raise ValueError("oops")

    partial = functools.partial(boom)
    try:
        _worker_wrapper(partial)
        assert False, "should have raised"
    except ValueError as e:
        assert str(e) == "oops"


def double(x):
    return x * 2


@pytest.mark.asyncio
async def test_process_task_initial_metadata():
    loop = asyncio.get_event_loop()
    task = ProcessTask(double, (4,), {}, loop=loop, executor=None, cancel_timeout=5.0)

    assert task.func_name == "double"
    assert task.args == (4,)
    assert task.kwargs == {}
    assert task.pid is None
    assert task.status == "pending"
    assert task.end_time is None
    assert task.duration is None
    assert task.exception is None
    assert task.cancel_timeout == 5.0
    assert isinstance(task.start_time, float)

    # clean up — we won't await it here
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass


@pytest.mark.asyncio
async def test_process_task_completes_and_sets_metadata():
    loop = asyncio.get_event_loop()
    task = ProcessTask(double, (6,), {}, loop=loop, executor=None, cancel_timeout=5.0)
    result = await task

    assert result == 12
    assert task.status == "done"
    assert task.pid is not None
    assert isinstance(task.pid, int)
    assert task.end_time is not None
    assert task.duration is not None
    assert task.duration >= 0.0


def add(x, y):
    return x + y


@pytest.mark.asyncio
async def test_process_task_supports_kwargs():
    loop = asyncio.get_event_loop()
    task = ProcessTask(add, (), {"x": 3, "y": 7}, loop=loop, executor=None, cancel_timeout=5.0)
    result = await task
    assert result == 10
    assert task.status == "done"


def always_raises():
    raise RuntimeError("worker exploded")


@pytest.mark.asyncio
async def test_process_task_failed_status_on_exception():
    loop = asyncio.get_event_loop()
    task = ProcessTask(always_raises, (), {}, loop=loop, executor=None, cancel_timeout=5.0)
    with pytest.raises(RuntimeError, match="worker exploded"):
        await task
    assert task.status == "failed"
    assert isinstance(task.exception, RuntimeError)
    assert task.end_time is not None
    assert task.duration is not None


class _Unpicklable:
    def __reduce__(self):
        raise TypeError("cannot pickle")


def uses_unpicklable(obj):
    return obj


@pytest.mark.asyncio
async def test_process_task_pickling_error_sets_failed():
    from concurrent.futures import ProcessPoolExecutor
    loop = asyncio.get_event_loop()
    executor = ProcessPoolExecutor(max_workers=1)
    try:
        task = ProcessTask(
            uses_unpicklable,
            (_Unpicklable(),),
            {},
            loop=loop,
            executor=executor,
            cancel_timeout=5.0,
        )
        with pytest.raises(Exception):
            await task
        assert task.status == "failed"
        assert task.exception is not None
    finally:
        executor.shutdown(wait=True)


import signal
from unittest.mock import patch as mock_patch


@pytest.mark.asyncio
async def test_cancel_with_known_pid_sends_sigterm():
    """cancel() sends SIGTERM when pid is known; task raises CancelledError."""
    loop = asyncio.get_event_loop()

    def slow():
        import time
        time.sleep(10)

    task = ProcessTask(slow, (), {}, loop=loop, executor=None, cancel_timeout=0.1)

    # Give it a moment to start so pid is captured
    await asyncio.sleep(0.3)

    with mock_patch("os.kill") as mock_kill:
        # Simulate pid already set
        task.pid = 12345
        task.cancel()

    mock_kill.assert_any_call(12345, signal.SIGTERM)
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass
    assert task.status == "cancelled"


@pytest.mark.asyncio
async def test_cancel_without_pid_falls_back_to_super():
    """cancel() with no pid still cancels the task gracefully."""
    loop = asyncio.get_event_loop()

    def slow():
        import time
        time.sleep(10)

    task = ProcessTask(slow, (), {}, loop=loop, executor=None, cancel_timeout=5.0)
    assert task.pid is None

    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass

    assert task.status == "cancelled"
