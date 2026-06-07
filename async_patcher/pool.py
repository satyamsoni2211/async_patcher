from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from types import TracebackType

from .patch import get_default_executor, set_default_executor


class process_pool:  # noqa: N801  (public API: snake_case matches asyncpg/aiohttp-style)
    """Async-friendly context manager that owns a :class:`ProcessPoolExecutor`,
    sets it as the module-level default for the duration of the block, and
    shuts it down on exit.

    Usage::

        async with async_patcher.process_pool(max_workers=4) as pool:
            task = asyncio.to_process(crunch_numbers, data)
            result = await task
    """

    def __init__(self, max_workers: int | None = None) -> None:
        self._max_workers = max_workers
        self._executor: ProcessPoolExecutor | None = None
        self._previous_default = None

    async def __aenter__(self) -> ProcessPoolExecutor:
        self._previous_default = get_default_executor()
        self._executor = ProcessPoolExecutor(max_workers=self._max_workers)
        set_default_executor(self._executor)
        return self._executor

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None
        set_default_executor(self._previous_default)
