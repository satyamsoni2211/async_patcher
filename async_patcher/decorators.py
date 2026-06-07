from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Callable, Optional, Union


def run_in_process(
    func: Optional[Callable] = None,
    *,
    executor: Optional[ProcessPoolExecutor] = None,
    cancel_timeout: float = 5.0,
) -> Union[Callable, Callable[[Callable], Callable]]:
    """Decorator: run the wrapped function in a separate process on every call.

    Usable with or without arguments::

        @async_patcher.run_in_process
        def heavy(x): ...

        @async_patcher.run_in_process(cancel_timeout=2.0)
        def heavy(x): ...

        @async_patcher.run_in_process(executor=my_pool)
        def heavy(x): ...

    Calling the decorated function returns a :class:`ProcessTask` — await it
    to retrieve the result (or surface the worker's exception).
    """

    def decorate(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return asyncio.to_process(
                fn,
                *args,
                executor=executor,
                cancel_timeout=cancel_timeout,
                **kwargs,
            )

        return wrapper

    if func is not None and callable(func):
        return decorate(func)
    return decorate
