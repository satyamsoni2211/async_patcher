# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.1.0] — 2026-06-07

### Added

- `asyncio.to_process(fn, *args, **kwargs)` — module-level entry point patched onto
  `asyncio` on import. Returns an awaitable `ProcessTask`.
- `loop.to_process(fn, *args, **kwargs)` — equivalent method patched onto
  `asyncio.BaseEventLoop`.
- `ProcessTask` — `asyncio.Task` subclass carrying `pid`, `func_name`, `args`,
  `kwargs`, `start_time`, `end_time`, `duration`, `status`, `exception`, and
  `cancel_timeout`.
- `TaskStatus(str, Enum)` — typed enum for all lifecycle states (`PENDING`, `RUNNING`,
  `DONE`, `FAILED`, `CANCELLED`). String comparisons (`task.status == "done"`) work
  unchanged via the `str` mixin.
- `__repr__` on `ProcessTask` — surfaces `func_name`, `status`, `pid`, and `duration`
  for readable output in debuggers and `asyncio.all_tasks()`.
- `__version__` export — reads from `importlib.metadata` at import time; falls back to
  a hardcoded string for unpacked source trees.
- `set_default_executor()` / `get_default_executor()` — module-level helpers to set a
  shared `ProcessPoolExecutor` once; all `to_process()` calls pick it up automatically.
- `process_pool(max_workers)` — async context manager that creates a pool, sets it as
  the module default, and shuts it down cleanly on exit, restoring the previous default.
- `@run_in_process` decorator — bare (`@run_in_process`) and parameterised
  (`@run_in_process(executor=..., cancel_timeout=...)`) forms. Calling a decorated
  function from a coroutine returns an awaitable `ProcessTask`. `functools.wraps`
  preserves `__name__` and `__doc__`.
- `timeout` parameter on `to_process()` — raises `TimeoutError` and triggers the
  SIGTERM → SIGKILL sequence when the worker exceeds a wall-clock limit.
- `cancel_timeout` parameter — per-task configurable window between SIGTERM and SIGKILL
  (default 5 s).
- `executor` parameter — bring your own `ProcessPoolExecutor` per call.
- Lifecycle callbacks — `on_start`, `on_done`, `on_error` optional callables passed to
  `to_process()`; fired at each lifecycle transition with the task instance. Callback
  exceptions are logged at `WARNING` level and never affect the awaiter.
- Graceful cancellation — `SIGTERM` on `cancel()`, `SIGKILL` after `cancel_timeout`
  seconds. Unix only; raises `NotImplementedError` on Windows when a PID is known.
- Eager PID capture via `multiprocessing.Pipe` — worker PID is available immediately
  after the worker starts, before the result is returned.
- Full type support — `py.typed` PEP 561 marker and `.pyi` stub files for all public
  modules (`__init__`, `task`, `patch`, `decorators`, `pool`). Passes `mypy --strict`.
- Idempotent patching — importing `async_patcher` multiple times is safe.
- Zero runtime dependencies — pure Python stdlib.
- Python 3.9–3.14 support.
- CI with pytest, pytest-asyncio, pytest-cov, and Codecov (67 tests across 12 files).
- MIT license.

---

[Unreleased]: https://github.com/satyamsoni2211/async_patcher/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/satyamsoni2211/async_patcher/releases/tag/v0.1.0