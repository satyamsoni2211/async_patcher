from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Callable, overload

@overload
def run_in_process(
    func: Callable[..., Any],
    *,
    executor: ProcessPoolExecutor | None = ...,
    cancel_timeout: float = ...,
) -> Callable[..., Any]: ...
@overload
def run_in_process(
    func: None = ...,
    *,
    executor: ProcessPoolExecutor | None = ...,
    cancel_timeout: float = ...,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
