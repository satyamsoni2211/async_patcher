from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ProcessPoolExecutor
from enum import Enum
from typing import Any, Callable

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

def _worker_wrapper(partial_fn: functools.partial[Any]) -> tuple[int, Any]: ...
def _worker_wrapper_with_pid(
    partial_fn: functools.partial[Any],
    child_conn: Any,
) -> tuple[int, Any]: ...

class ProcessTask(asyncio.Task[Any]):
    func_name: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    pid: int | None
    start_time: float
    end_time: float | None
    duration: float | None
    status: TaskStatus
    exception: BaseException  # type: ignore[assignment]
    cancel_timeout: float
    timeout: float | None
    def __init__(
        self,
        func: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        *,
        loop: asyncio.AbstractEventLoop,
        executor: ProcessPoolExecutor,
        cancel_timeout: float = ...,
        timeout: float | None = ...,
        on_start: Callable[[ProcessTask], None] | None = ...,
        on_done: Callable[[ProcessTask], None] | None = ...,
        on_error: Callable[[ProcessTask], None] | None = ...,
    ) -> None: ...
    def cancel(self, msg: Any = ...) -> bool: ...
    def __repr__(self) -> str: ...
