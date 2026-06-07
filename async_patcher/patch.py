from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Callable

from .task import ProcessTask

_patched = False
_default_executor: ProcessPoolExecutor | None = None


def set_default_executor(executor: ProcessPoolExecutor | None) -> None:
    """Set the module-level default executor used by ``to_process()`` when
    no executor is explicitly provided.

    Pass ``None`` to clear the default.
    """
    global _default_executor
    _default_executor = executor


def get_default_executor() -> ProcessPoolExecutor | None:
    """Return the module-level default executor, or ``None`` if not set."""
    return _default_executor


def _resolve_executor(
    executor: ProcessPoolExecutor | None,
) -> ProcessPoolExecutor | None:
    """Pick the executor: explicit arg > module default > None."""
    if executor is not None:
        return executor
    return _default_executor


def _make_process_task(
    func: Callable,
    args: tuple,
    kwargs: dict,
    loop: asyncio.AbstractEventLoop,
    executor: Any,
    cancel_timeout: float,
    timeout: float | None = None,
    on_start: Callable[[ProcessTask], None] | None = None,
    on_done: Callable[[ProcessTask], None] | None = None,
    on_error: Callable[[ProcessTask], None] | None = None,
) -> ProcessTask:
    """Internal factory — constructs and schedules a ProcessTask."""
    return ProcessTask(
        func,
        args,
        kwargs,
        loop=loop,
        executor=executor,
        cancel_timeout=cancel_timeout,
        timeout=timeout,
        on_start=on_start,
        on_done=on_done,
        on_error=on_error,
    )


def _module_to_process(
    func: Callable,
    /,
    *args: Any,
    executor: Any = None,
    cancel_timeout: float = 5.0,
    timeout: float | None = None,
    on_start: Callable[[ProcessTask], None] | None = None,
    on_done: Callable[[ProcessTask], None] | None = None,
    on_error: Callable[[ProcessTask], None] | None = None,
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
    return _make_process_task(
        func,
        args,
        kwargs,
        loop,
        _resolve_executor(executor),
        cancel_timeout,
        timeout,
        on_start,
        on_done,
        on_error,
    )


def _loop_to_process(
    self: asyncio.AbstractEventLoop,
    func: Callable,
    /,
    *args: Any,
    executor: Any = None,
    cancel_timeout: float = 5.0,
    timeout: float | None = None,
    on_start: Callable[[ProcessTask], None] | None = None,
    on_done: Callable[[ProcessTask], None] | None = None,
    on_error: Callable[[ProcessTask], None] | None = None,
    **kwargs: Any,
) -> ProcessTask:
    """loop.to_process — bound-method entry point."""
    return _make_process_task(
        func,
        args,
        kwargs,
        self,
        _resolve_executor(executor),
        cancel_timeout,
        timeout,
        on_start,
        on_done,
        on_error,
    )


def patch() -> None:
    """Monkey-patch asyncio with to_process. Idempotent."""
    global _patched
    if _patched:
        return

    asyncio.to_process = _module_to_process  # type: ignore[attr-defined]
    asyncio.BaseEventLoop.to_process = _loop_to_process  # type: ignore[attr-defined]

    _patched = True
