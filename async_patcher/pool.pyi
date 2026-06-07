from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from types import TracebackType

class process_pool:  # noqa: N801  (public API: snake_case matches asyncpg/aiohttp-style)
    def __init__(self, max_workers: int | None = ...) -> None: ...
    async def __aenter__(self) -> ProcessPoolExecutor: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
