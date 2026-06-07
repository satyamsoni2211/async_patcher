from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Callable, Optional

from .task import ProcessTask

def patch() -> None: ...
def set_default_executor(executor: Optional[ProcessPoolExecutor]) -> None: ...
def get_default_executor() -> Optional[ProcessPoolExecutor]: ...
def _resolve_executor(
    executor: Optional[ProcessPoolExecutor],
) -> Optional[ProcessPoolExecutor]: ...
def _make_process_task(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    loop: asyncio.AbstractEventLoop,
    executor: Any,
    cancel_timeout: float,
    timeout: Optional[float] = ...,
    on_start: Optional[Callable[[ProcessTask], None]] = ...,
    on_done: Optional[Callable[[ProcessTask], None]] = ...,
    on_error: Optional[Callable[[ProcessTask], None]] = ...,
) -> ProcessTask: ...
def _module_to_process(
    func: Callable[..., Any],
    /,
    *args: Any,
    executor: Optional[ProcessPoolExecutor] = ...,
    cancel_timeout: float = ...,
    timeout: Optional[float] = ...,
    on_start: Optional[Callable[[ProcessTask], None]] = ...,
    on_done: Optional[Callable[[ProcessTask], None]] = ...,
    on_error: Optional[Callable[[ProcessTask], None]] = ...,
    **kwargs: Any,
) -> ProcessTask: ...
def _loop_to_process(
    self: asyncio.AbstractEventLoop,
    func: Callable[..., Any],
    /,
    *args: Any,
    executor: Optional[ProcessPoolExecutor] = ...,
    cancel_timeout: float = ...,
    timeout: Optional[float] = ...,
    on_start: Optional[Callable[[ProcessTask], None]] = ...,
    on_done: Optional[Callable[[ProcessTask], None]] = ...,
    on_error: Optional[Callable[[ProcessTask], None]] = ...,
    **kwargs: Any,
) -> ProcessTask: ...
