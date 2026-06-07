from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Callable, Optional, Union, overload

@overload
def run_in_process(
    func: Callable[..., Any],
    *,
    executor: Optional[ProcessPoolExecutor] = ...,
    cancel_timeout: float = ...,
) -> Callable[..., Any]: ...
@overload
def run_in_process(
    func: None = ...,
    *,
    executor: Optional[ProcessPoolExecutor] = ...,
    cancel_timeout: float = ...,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
