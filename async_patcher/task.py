from __future__ import annotations

import asyncio
import functools
import logging
import multiprocessing
import os
import signal
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Lifecycle status of a ProcessTask.

    Inherits from ``str`` so existing ``task.status == "done"`` comparisons
    keep working unchanged.
    """

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _worker_wrapper(partial_fn: functools.partial) -> tuple[int, Any]:
    """Run *partial_fn* in the worker process, return (pid, result).

    This must be a top-level function so it is picklable by ProcessPoolExecutor.
    """
    pid = os.getpid()
    result = partial_fn()
    return pid, result


def _worker_wrapper_with_pid(
    partial_fn: functools.partial,
    child_conn: "multiprocessing.connection.Connection",
) -> tuple[int, Any]:
    """Same as ``_worker_wrapper`` but also writes the worker pid to
    *child_conn* as the very first action, so the parent can learn the pid
    before the work completes (used to support timeouts)."""
    child_conn.send_bytes(str(os.getpid()).encode())
    child_conn.close()
    return _worker_wrapper(partial_fn)


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
    status : TaskStatus
        Lifecycle status. See :class:`TaskStatus`.
    exception : BaseException | None
        Populated when status is 'failed'.
    cancel_timeout : float
        Seconds to wait between SIGTERM and SIGKILL (default 5.0).
    timeout : float | None
        Optional maximum seconds to wait for the worker to finish. On expiry,
        the worker is sent SIGTERM (then SIGKILL) and asyncio.TimeoutError is
        raised to the awaiter.
    """

    def __init__(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        *,
        loop: asyncio.AbstractEventLoop,
        executor: ProcessPoolExecutor,
        cancel_timeout: float = 5.0,
        timeout: Optional[float] = None,
        on_start: Optional[Callable[["ProcessTask"], None]] = None,
        on_done: Optional[Callable[["ProcessTask"], None]] = None,
        on_error: Optional[Callable[["ProcessTask"], None]] = None,
    ) -> None:
        self.func_name: str = func.__name__
        self.args: tuple = args
        self.kwargs: dict = kwargs
        self.pid: Optional[int] = None
        self.start_time: float = time.monotonic()
        self.end_time: Optional[float] = None
        self.duration: Optional[float] = None
        self.status: TaskStatus = TaskStatus.PENDING
        self.exception: Optional[BaseException] = None
        self.cancel_timeout: float = cancel_timeout
        self.timeout: Optional[float] = timeout
        self._on_start = on_start
        self._on_done = on_done
        self._on_error = on_error
        self._executor = executor
        self._proc_loop = loop
        self._parent_conn, self._child_conn = multiprocessing.Pipe(duplex=False)
        self._pid_watcher_installed = False

        partial_fn = functools.partial(func, *args, **kwargs)
        super().__init__(
            self._run(partial_fn),
            loop=loop,
        )

    def _install_pid_watcher(self) -> None:
        """Subscribe to the parent end of the pid pipe so we can capture
        the worker pid as soon as the worker writes it."""
        if self._pid_watcher_installed:
            return
        self._pid_watcher_installed = True
        try:
            self._proc_loop.add_reader(
                self._parent_conn.fileno(), self._capture_worker_pid
            )
        except (NotImplementedError, OSError):
            # add_reader not available (e.g. Windows SelectorLoop with proactor);
            # pid will fall back to being set after the future resolves.
            self._pid_watcher_installed = False

    def _capture_worker_pid(self) -> None:
        """Reader callback: read the pid from the pipe and store it."""
        try:
            if self._parent_conn.poll(0):
                data = self._parent_conn.recv_bytes()
                self.pid = int(data)
        except (EOFError, ValueError, OSError):
            pass
        finally:
            try:
                self._proc_loop.remove_reader(self._parent_conn.fileno())
            except (OSError, ValueError):
                pass

    def _drain_pipe(self) -> None:
        """Best-effort: read any pending bytes from the pipe (non-blocking)
        and uninstall the reader. Used on completion so we don't leak the fd."""
        try:
            while self._parent_conn.poll(0):
                data = self._parent_conn.recv_bytes()
                if self.pid is None:
                    try:
                        self.pid = int(data)
                    except ValueError:
                        pass
        except (EOFError, OSError):
            pass
        if self._pid_watcher_installed:
            try:
                self._proc_loop.remove_reader(self._parent_conn.fileno())
            except (OSError, ValueError):
                pass
            self._pid_watcher_installed = False

    async def _run(self, partial_fn: functools.partial) -> Any:
        """Coroutine submitted to asyncio.Task; drives the executor call."""
        self.status = TaskStatus.RUNNING
        self._fire_callback(self._on_start)
        try:
            if self.timeout is not None:
                return await self._run_with_timeout(partial_fn)
            return await self._run_plain(partial_fn)
        except asyncio.CancelledError:
            self.status = TaskStatus.CANCELLED
            raise
        except asyncio.TimeoutError as exc:
            # Best-effort: kill the worker so it doesn't keep running.
            self._send_term_if_known_pid()
            self.status = TaskStatus.FAILED
            self.exception = exc
            self._fire_callback(self._on_error)
            raise
        except Exception as exc:
            self.status = TaskStatus.FAILED
            self.exception = exc
            self._fire_callback(self._on_error)
            raise
        finally:
            self.end_time = time.monotonic()
            self.duration = self.end_time - self.start_time

    def _fire_callback(
        self, callback: Optional[Callable[["ProcessTask"], None]]
    ) -> None:
        """Call *callback* (if set) with self. Exceptions raised by the
        callback are logged but do not propagate."""
        if callback is None:
            return
        try:
            callback(self)
        except Exception:
            logger.warning("async_patcher: lifecycle callback raised", exc_info=True)

    async def _run_plain(self, partial_fn: functools.partial) -> Any:
        self._install_pid_watcher()
        try:
            pid, result = await self._proc_loop.run_in_executor(
                self._executor, _worker_wrapper_with_pid, partial_fn, self._child_conn
            )
            if self.pid is None:
                self.pid = pid
            self.status = TaskStatus.DONE
            self.end_time = time.monotonic()
            self.duration = self.end_time - self.start_time
            self._fire_callback(self._on_done)
            return result
        finally:
            self._drain_pipe()

    async def _run_with_timeout(self, partial_fn: functools.partial) -> Any:
        self._install_pid_watcher()
        try:
            pid, result = await asyncio.wait_for(
                self._proc_loop.run_in_executor(
                    self._executor,
                    _worker_wrapper_with_pid,
                    partial_fn,
                    self._child_conn,
                ),
                timeout=self.timeout,
            )
            if self.pid is None:
                self.pid = pid
            self.status = TaskStatus.DONE
            self.end_time = time.monotonic()
            self.duration = self.end_time - self.start_time
            self._fire_callback(self._on_done)
            return result
        finally:
            self._drain_pipe()

    def _send_term_if_known_pid(self) -> None:
        """Send SIGTERM to the worker if we already know its pid, and
        schedule a SIGKILL fallback. No-op if the pid is unknown."""
        if self.pid is None or sys.platform == "win32":
            return
        try:
            os.kill(self.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except Exception:
            logger.warning(
                "async_patcher: could not SIGTERM pid %s", self.pid, exc_info=True
            )
            return
        self._proc_loop.call_later(
            self.cancel_timeout, self._sigkill_if_alive, self.pid
        )

    def cancel(self, msg: Any = None) -> bool:
        """Cancel the task.

        If the worker PID is known, send SIGTERM immediately. After
        *cancel_timeout* seconds, send SIGKILL if the process is still alive.
        Always calls super().cancel() to propagate CancelledError to awaiters.

        Raises
        ------
        NotImplementedError
            If running on Windows with a known worker PID. Windows has no
            SIGTERM/SIGKILL semantics that map cleanly to the Unix escalation
            used here; failing loudly is better than silently leaving the
            worker process running.
        """
        if self.pid is not None and sys.platform == "win32":
            raise NotImplementedError(
                "async_patcher.ProcessTask.cancel() does not support Windows: "
                "the SIGTERM/SIGKILL escalation has no portable Windows "
                "equivalent. The asyncio cancellation is still applied, but "
                "the worker process may continue running until it exits "
                "naturally."
            )
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
        if result and self.status == TaskStatus.PENDING:
            self.status = TaskStatus.CANCELLED
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

    def __repr__(self) -> str:
        duration = f"{self.duration:.4f}s" if self.duration is not None else "n/a"
        pid = self.pid if self.pid is not None else "n/a"
        return (
            f"<ProcessTask func={self.func_name!r} "
            f"status={self.status.value!r} "
            f"pid={pid} "
            f"duration={duration}>"
        )
