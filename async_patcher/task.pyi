from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ProcessPoolExecutor
from enum import Enum
from typing import Any, Callable, Optional

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
    pid: Optional[int]
    start_time: float
    end_time: Optional[float]
    duration: Optional[float]
    status: TaskStatus
    exception: BaseException  # type: ignore[assignment]
    cancel_timeout: float
    timeout: Optional[float]
    def __init__(
        self,
        func: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        *,
        loop: asyncio.AbstractEventLoop,
        executor: ProcessPoolExecutor,
        cancel_timeout: float = ...,
        timeout: Optional[float] = ...,
        on_start: Optional[Callable[[ProcessTask], None]] = ...,
        on_done: Optional[Callable[[ProcessTask], None]] = ...,
        on_error: Optional[Callable[[ProcessTask], None]] = ...,
    ) -> None: ...
    def cancel(self, msg: Any = ...) -> bool: ...
    def __repr__(self) -> str: ...
