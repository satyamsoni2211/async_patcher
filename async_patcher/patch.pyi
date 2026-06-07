from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Callable

from .task import ProcessTask

def patch() -> None: ...
def set_default_executor(executor: ProcessPoolExecutor | None) -> None: ...
def get_default_executor() -> ProcessPoolExecutor | None: ...
def _resolve_executor(
    executor: ProcessPoolExecutor | None,
) -> ProcessPoolExecutor | None: ...
def _make_process_task(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    loop: asyncio.AbstractEventLoop,
    executor: Any,
    cancel_timeout: float,
    timeout: float | None = ...,
    on_start: Callable[[ProcessTask], None] | None = ...,
    on_done: Callable[[ProcessTask], None] | None = ...,
    on_error: Callable[[ProcessTask], None] | None = ...,
) -> ProcessTask: ...
def _module_to_process(
    func: Callable[..., Any],
    /,
    *args: Any,
    executor: ProcessPoolExecutor | None = ...,
    cancel_timeout: float = ...,
    timeout: float | None = ...,
    on_start: Callable[[ProcessTask], None] | None = ...,
    on_done: Callable[[ProcessTask], None] | None = ...,
    on_error: Callable[[ProcessTask], None] | None = ...,
    **kwargs: Any,
) -> ProcessTask: ...
def _loop_to_process(
    self: asyncio.AbstractEventLoop,
    func: Callable[..., Any],
    /,
    *args: Any,
    executor: ProcessPoolExecutor | None = ...,
    cancel_timeout: float = ...,
    timeout: float | None = ...,
    on_start: Callable[[ProcessTask], None] | None = ...,
    on_done: Callable[[ProcessTask], None] | None = ...,
    on_error: Callable[[ProcessTask], None] | None = ...,
    **kwargs: Any,
) -> ProcessTask: ...
