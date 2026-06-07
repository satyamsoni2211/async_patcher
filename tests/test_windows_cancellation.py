"""Tests that cancel() fails loudly on Windows instead of silently no-oping."""
import asyncio
import pytest

from async_patcher.task import ProcessTask


def double(x):
    return x * 2


@pytest.mark.asyncio
async def test_cancel_on_windows_raises_not_implemented_when_pid_known():
    loop = asyncio.get_event_loop()
    task = ProcessTask(double, (1,), {}, loop=loop, executor=None, cancel_timeout=5.0)

    # Simulate: task has captured a real worker pid
    task.pid = 99999

    with pytest.MonkeyPatch.context() as m:
        m.setattr("sys.platform", "win32")
        with pytest.raises(NotImplementedError, match="[Ww]indows"):
            task.cancel()

    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass


@pytest.mark.asyncio
async def test_cancel_on_windows_succeeds_when_no_pid_yet():
    """Before the worker has started, Windows cancellation still works
    because we just delegate to super().cancel()."""
    loop = asyncio.get_event_loop()
    task = ProcessTask(double, (1,), {}, loop=loop, executor=None, cancel_timeout=5.0)

    assert task.pid is None

    with pytest.MonkeyPatch.context() as m:
        m.setattr("sys.platform", "win32")
        # Should NOT raise — there's no pid to kill
        task.cancel()

    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass


@pytest.mark.asyncio
async def test_cancel_on_linux_still_works():
    """Regression: on non-Windows, cancel() does not raise NotImplementedError."""
    loop = asyncio.get_event_loop()
    task = ProcessTask(double, (1,), {}, loop=loop, executor=None, cancel_timeout=5.0)
    task.pid = 99999

    with pytest.MonkeyPatch.context() as m:
        m.setattr("sys.platform", "linux")
        m.setattr("async_patcher.task.os.kill", lambda *a, **kw: None)
        m.setattr("async_patcher.task.signal.SIGTERM", 15)
        m.setattr("async_patcher.task.signal.SIGKILL", 9)
        # Should not raise
        task.cancel()

    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass
