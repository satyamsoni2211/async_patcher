from __future__ import annotations

import asyncio
from typing import Any, Callable

from .task import ProcessTask

_patched = False


def _make_process_task(
    func: Callable,
    args: tuple,
    kwargs: dict,
    loop: asyncio.AbstractEventLoop,
    executor: Any,
    cancel_timeout: float,
) -> ProcessTask:
    """Internal factory — constructs and schedules a ProcessTask."""
    return ProcessTask(
        func,
        args,
        kwargs,
        loop=loop,
        executor=executor,
        cancel_timeout=cancel_timeout,
    )


def _module_to_process(
    func: Callable,
    /,
    *args: Any,
    executor: Any = None,
    cancel_timeout: float = 5.0,
    **kwargs: Any,
) -> ProcessTask:
    """asyncio.to_process — module-level entry point."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        raise RuntimeError(
            "asyncio.to_process() requires a running event loop. "
            "Call it from inside a coroutine or an async context."
        ) from None
    return _make_process_task(func, args, kwargs, loop, executor, cancel_timeout)


def _loop_to_process(
    self: asyncio.AbstractEventLoop,
    func: Callable,
    /,
    *args: Any,
    executor: Any = None,
    cancel_timeout: float = 5.0,
    **kwargs: Any,
) -> ProcessTask:
    """loop.to_process — bound-method entry point."""
    return _make_process_task(func, args, kwargs, self, executor, cancel_timeout)


def patch() -> None:
    """Monkey-patch asyncio with to_process. Idempotent."""
    global _patched
    if _patched:
        return

    asyncio.to_process = _module_to_process  # type: ignore[attr-defined]
    asyncio.BaseEventLoop.to_process = _loop_to_process  # type: ignore[attr-defined]

    _patched = True
