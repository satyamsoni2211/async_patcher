from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from types import TracebackType
from typing import Optional, Type

class process_pool:
    def __init__(self, max_workers: Optional[int] = ...) -> None: ...
    async def __aenter__(self) -> ProcessPoolExecutor: ...
    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None: ...
