from __future__ import annotations

import asyncio
import functools
import logging
import os
import signal
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Callable

logger = logging.getLogger(__name__)


def _worker_wrapper(partial_fn: functools.partial) -> tuple[int, Any]:
    """Run *partial_fn* in the worker process, return (pid, result).

    This must be a top-level function so it is picklable by ProcessPoolExecutor.
    """
    pid = os.getpid()
    result = partial_fn()
    return pid, result


class ProcessTask(asyncio.Task):
    """An asyncio.Task that runs *func* in a separate process.

    Attributes
    ----------
    pid : int | None
        Worker process PID. None until the process has started.
    func_name : str
        Name of the callable that was submitted.
    args : tuple
        Positional arguments passed to the callable.
    kwargs : dict
        Keyword arguments passed to the callable.
    start_time : float
        Monotonic timestamp recorded at construction.
    end_time : float | None
        Monotonic timestamp recorded on completion, failure, or cancel.
    duration : float | None
        end_time - start_time, set alongside end_time.
    status : str
        One of: pending, running, done, failed, cancelled.
    exception : BaseException | None
        Populated when status is 'failed'.
    cancel_timeout : float
        Seconds to wait between SIGTERM and SIGKILL (default 5.0).
    """

    def __init__(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        *,
        loop: asyncio.AbstractEventLoop,
        executor: Any,
        cancel_timeout: float = 5.0,
    ) -> None:
        self.func_name: str = func.__name__
        self.args: tuple = args
        self.kwargs: dict = kwargs
        self.pid: int | None = None
        self.start_time: float = time.monotonic()
        self.end_time: float | None = None
        self.duration: float | None = None
        self.status: str = "pending"
        self.exception: BaseException | None = None
        self.cancel_timeout: float = cancel_timeout
        self._executor = executor
        self._proc_loop = loop

        partial_fn = functools.partial(func, *args, **kwargs)
        super().__init__(
            self._run(partial_fn),
            loop=loop,
        )

    async def _run(self, partial_fn: functools.partial) -> Any:
        """Coroutine submitted to asyncio.Task; drives the executor call."""
        self.status = "running"
        try:
            pid, result = await self._proc_loop.run_in_executor(
                self._executor, _worker_wrapper, partial_fn
            )
            self.pid = pid
            self.status = "done"
            return result
        except asyncio.CancelledError:
            self.status = "cancelled"
            raise
        except Exception as exc:
            self.status = "failed"
            self.exception = exc
            raise
        finally:
            self.end_time = time.monotonic()
            self.duration = self.end_time - self.start_time

    def cancel(self, msg: Any = None) -> bool:
        """Cancel the task.

        If the worker PID is known, send SIGTERM immediately. After
        *cancel_timeout* seconds, send SIGKILL if the process is still alive.
        Always calls super().cancel() to propagate CancelledError to awaiters.
        """
        if self.pid is not None:
            try:
                os.kill(self.pid, signal.SIGTERM)
            except ProcessLookupError:
                # Process already exited — nothing to do
                pass
            except Exception:
                logger.warning(
                    "async_patcher: could not SIGTERM pid %s", self.pid, exc_info=True
                )
            else:
                # Schedule SIGKILL after cancel_timeout seconds
                self._proc_loop.call_later(
                    self.cancel_timeout, self._sigkill_if_alive, self.pid
                )
        result = super().cancel(msg)
        if result and self.status == "pending":
            self.status = "cancelled"
            self.end_time = time.monotonic()
            self.duration = self.end_time - self.start_time
        return result

    def _sigkill_if_alive(self, pid: int) -> None:
        """Send SIGKILL to *pid* if the process is still running."""
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # already gone — normal case
        except Exception:
            logger.warning(
                "async_patcher: could not SIGKILL pid %s", pid, exc_info=True
            )
