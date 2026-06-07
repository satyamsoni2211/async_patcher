# async-patcher

[![Python Version](https://img.shields.io/badge/python-3.9%20|%203.10%20|%203.11%20|%203.12%20|%203.13%20|%203.14-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/satyamsoni2211/async_patcher/actions/workflows/ci.yml/badge.svg)](https://github.com/satyamsoni2211/async_patcher/actions/workflows/ci.yml)
[![Codecov](https://img.shields.io/codecov/c/github/satyamsoni2211/async_patcher)
](https://codecov.io/gh/satyamsoni2211/async_patcher)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/async_patcher)
](pypi.org/project/async-patcher/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](#installation)
[![Typed](https://img.shields.io/badge/typing-py.typed%20%2B%20stubs-informational.svg)](#typed-stubs--py.typed)

> Seamlessly offload CPU-bound work from your asyncio event loop to separate processes — with full tracking, rich metadata, graceful cancellation, lifecycle callbacks, and first-class type support.

`async-patcher` monkey-patches the `asyncio` module on import to add a `to_process` method available both at the module level (`asyncio.to_process(...)`) and on any running event loop (`loop.to_process(...)`). It returns a `ProcessTask` — a proper `asyncio.Task` subclass that is awaitable, cancellable, and carries detailed execution metadata including the worker PID, timing, status, and any exceptions raised.

---

## Table of Contents

- [Why async-patcher?](#why-async-patcher)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Basic Usage](#basic-usage)
  - [Using with the Event Loop](#using-with-the-event-loop)
  - [Passing Keyword Arguments](#passing-keyword-arguments)
  - [Custom Executor](#custom-executor)
  - [Default Executor](#default-executor)
  - [Process Pool Context Manager](#process-pool-context-manager)
  - [Run-in-Process Decorator](#run-in-process-decorator)
  - [Timeout Support](#timeout-support)
  - [Custom Cancellation Timeout](#custom-cancellation-timeout)
  - [Lifecycle Callbacks](#lifecycle-callbacks)
  - [Tracking with ProcessTask](#tracking-with-processtask)
  - [Handling Failures](#handling-failures)
  - [Cancellation](#cancellation)
- [API Reference](#api-reference)
  - [asyncio.to_process](#asyncioto_process)
  - [loop.to_process](#loopto_process)
  - [ProcessTask](#processtask)
  - [TaskStatus](#taskstatus)
  - [set_default_executor / get_default_executor](#set_default_executor--get_default_executor)
  - [process_pool](#process_pool)
  - [run_in_process](#run_in_process)
- [Typed Stubs & py.typed](#typed-stubs--pytyped)
- [How It Works](#how-it-works)
- [Caveats & Limitations](#caveats--limitations)
- [Running Tests](#running-tests)
- [Contributing](#contributing)
- [License](#license)

---

## Why async-patcher?

The `asyncio` event loop is single-threaded. CPU-intensive work — image processing, number crunching, ML inference, compression — blocks the entire loop and starves all other coroutines.

The standard fix is `loop.run_in_executor(executor, fn, *args)`, but this has friction:

- It returns a bare `Future`, not a `Task` — you can't track it with `asyncio.all_tasks()`
- No built-in metadata: you don't know which function ran, what PID handled it, how long it took, or why it failed
- Cancellation is partial: the `Future` is cancelled but the worker process keeps running, consuming CPU

`async-patcher` solves all three — and goes further:

```python
import async_patcher  # one import — asyncio is patched

task = asyncio.to_process(crunch_numbers, dataset)
result = await task

print(f"Done in {task.duration:.2f}s on PID {task.pid}")
print(repr(task))  # <ProcessTask func='crunch_numbers' status='done' pid=84312 duration=0.0231s>
```

---

## Features

- **Zero-friction patching** — just `import async_patcher`; no explicit setup calls needed
- **Dual access points** — `asyncio.to_process(...)` at module level, `loop.to_process(...)` inside coroutines
- **Rich `ProcessTask` object** — full metadata: PID, function name, args/kwargs, timing, status, exception
- **Proper `asyncio.Task` subclass** — awaitable, cancellable, compatible with `asyncio.gather`, `asyncio.wait`, `asyncio.shield`
- **Graceful cancellation** — SIGTERM first, then SIGKILL after a configurable timeout
- **`TaskStatus` enum** — typed, string-comparable status values (`PENDING`, `RUNNING`, `DONE`, `FAILED`, `CANCELLED`)
- **`@run_in_process` decorator** — decorate any function to automatically dispatch it to a worker process
- **`timeout` parameter** — cancel and SIGTERM the worker if it exceeds a wall-clock limit
- **`process_pool()` context manager** — `async with process_pool(max_workers=4)` for scoped pool lifecycle
- **Default executor** — set a module-level default pool once; every call uses it without repetition
- **Lifecycle callbacks** — `on_start`, `on_done`, `on_error` hooks for observability and logging
- **Rich `__repr__`** — `<ProcessTask func='...' status='...' pid=... duration=...s>`
- **kwargs support** — pass keyword arguments naturally; `functools.partial` handles the rest
- **Idempotent patching** — importing `async_patcher` multiple times is safe
- **Full type support** — `py.typed` marker, `.pyi` stubs, passes `mypy --strict`
- **Python 3.9+** — works on 3.9 through 3.14; zero runtime dependencies

---

## Requirements

- Python **3.9** or newer
- No third-party runtime dependencies

---

## Installation

```bash
pip install async-patcher
```

Or with `uv`:

```bash
uv add async-patcher
```

Or install from source:

```bash
git clone https://github.com/satyamsoni2211/async_patcher.git
cd async_patcher
pip install -e .
```

---

## Quick Start

```python
import asyncio
import async_patcher  # patches asyncio on import


def cpu_intensive(n: int) -> int:
    """A CPU-bound function that would otherwise block the event loop."""
    return sum(i * i for i in range(n))


async def main():
    # Dispatch to a separate process — event loop stays free
    task = asyncio.to_process(cpu_intensive, 10_000_000)

    result = await task

    print(f"Result : {result}")
    print(f"Status : {task.status}")       # TaskStatus.DONE  (also == "done")
    print(f"PID    : {task.pid}")          # e.g. 84312
    print(f"Took   : {task.duration:.3f}s")
    print(repr(task))                      # <ProcessTask func='cpu_intensive' status='done' pid=84312 duration=0.023s>


asyncio.run(main())
```

---

## Usage

### Basic Usage

Import `async_patcher` once — anywhere in your application, typically at the top of your entry point:

```python
import async_patcher
```

From that point on, `asyncio.to_process` is available globally in your process.

```python
import asyncio

async def main():
    task = asyncio.to_process(my_function, arg1, arg2)
    result = await task

asyncio.run(main())
```

---

### Using with the Event Loop

Inside a coroutine you can call `to_process` directly on the running loop. This is equivalent to the module-level form but is more explicit about which loop is used:

```python
async def handler():
    loop = asyncio.get_event_loop()
    task = loop.to_process(compress_file, "/path/to/file.dat")
    result = await task
```

---

### Passing Keyword Arguments

Both positional and keyword arguments are fully supported:

```python
def resize_image(path: str, *, width: int, height: int) -> bytes:
    ...

async def main():
    task = asyncio.to_process(resize_image, "/img.png", width=800, height=600)
    data = await task
```

---

### Custom Executor

By default, `to_process` uses Python's default `ProcessPoolExecutor`. You can supply your own for fine-grained control over pool size, initializers, or resource limits:

```python
from concurrent.futures import ProcessPoolExecutor

executor = ProcessPoolExecutor(max_workers=4)

async def main():
    task = asyncio.to_process(my_fn, data, executor=executor)
    result = await task

    # Shut down the pool when done
    executor.shutdown(wait=True)
```

> **Tip:** A shared, long-lived executor avoids the overhead of spawning new processes on every call. Create it once at startup and reuse it across your application — or use [`process_pool()`](#process-pool-context-manager) to manage its lifecycle automatically.

---

### Default Executor

Set a module-level default executor once and every subsequent `to_process` call picks it up automatically — no need to pass `executor=` everywhere:

```python
import async_patcher
from async_patcher import set_default_executor, get_default_executor
from concurrent.futures import ProcessPoolExecutor

# At application startup
set_default_executor(ProcessPoolExecutor(max_workers=8))

async def main():
    # All of these use the shared pool automatically
    t1 = asyncio.to_process(job_a, data_a)
    t2 = asyncio.to_process(job_b, data_b)
    results = await asyncio.gather(t1, t2)

    # Inspect the current default
    pool = get_default_executor()
```

Passing `executor=` explicitly to `to_process` always wins over the module default.

---

### Process Pool Context Manager

`process_pool()` is an async context manager that creates a `ProcessPoolExecutor`, sets it as the module default for the duration of the block, and shuts it down cleanly on exit — restoring whatever default was set before:

```python
import async_patcher
from async_patcher import process_pool

async def main():
    async with process_pool(max_workers=4) as pool:
        # Inside this block, all to_process calls use the 4-worker pool
        t1 = asyncio.to_process(crunch_numbers, data1)
        t2 = asyncio.to_process(crunch_numbers, data2)
        results = await asyncio.gather(t1, t2)
    # Pool is shut down; previous default is restored
```

> **Note:** Only `async with` is supported — `with` (sync) is not.

---

### Run-in-Process Decorator

Decorate a function with `@run_in_process` and calling it from a coroutine automatically dispatches it to a worker process:

```python
from async_patcher import run_in_process

@run_in_process
def crunch_numbers(n: int) -> int:
    return sum(i * i for i in range(n))

async def main():
    result = await crunch_numbers(10_000_000)
```

Pass options via the parameterized form:

```python
from concurrent.futures import ProcessPoolExecutor
from async_patcher import run_in_process

pool = ProcessPoolExecutor(max_workers=4)

@run_in_process(executor=pool, cancel_timeout=2.0)
def render_frame(frame_id: int) -> bytes:
    ...

async def main():
    frame = await render_frame(42)
```

Both the bare (`@run_in_process`) and parameterized (`@run_in_process(...)`) forms are supported. `functools.wraps` preserves the original function's `__name__` and `__doc__`.

---

### Timeout Support

Pass `timeout=` to automatically cancel and clean up the worker if it exceeds a wall-clock limit:

```python
async def main():
    try:
        result = await asyncio.to_process(slow_job, data, timeout=10.0)
    except TimeoutError:
        print("Worker took too long — cancelled and killed")
```

On timeout:
1. `TimeoutError` is raised to the awaiter
2. `SIGTERM` is sent to the worker process
3. After `cancel_timeout` seconds, `SIGKILL` is sent if the process is still alive
4. `task.status` becomes `"failed"`

`timeout=None` (the default) means no limit.

---

### Custom Cancellation Timeout

When you cancel a `ProcessTask`, `async-patcher` sends `SIGTERM` to the worker process and waits `cancel_timeout` seconds before escalating to `SIGKILL`. The default is **5 seconds**. You can override this per-task:

```python
# Give the worker 30 seconds to clean up before force-killing
task = asyncio.to_process(long_running_job, data, cancel_timeout=30.0)

# Or be aggressive — kill immediately after SIGTERM
task = asyncio.to_process(stateless_fn, data, cancel_timeout=0.0)
```

---

### Lifecycle Callbacks

Attach callbacks to a task to react to status transitions — useful for logging, metrics, alerting, or updating a progress UI:

```python
from async_patcher import ProcessTask

def on_start(task: ProcessTask) -> None:
    print(f"[START] {task.func_name} pid={task.pid}")

def on_done(task: ProcessTask) -> None:
    print(f"[DONE]  {task.func_name} took {task.duration:.3f}s")

def on_error(task: ProcessTask) -> None:
    print(f"[ERROR] {task.func_name} failed: {task.exception}")

async def main():
    task = asyncio.to_process(
        process_batch,
        records,
        on_start=on_start,
        on_done=on_done,
        on_error=on_error,
    )
    result = await task
```

**Callback guarantees:**
- `on_start` fires after `status` transitions to `RUNNING` — `task.pid` is populated
- `on_done` fires after `duration` and `end_time` are set
- `on_error` fires for both worker exceptions and timeouts
- Callback exceptions are logged at `WARNING` level and swallowed — they never affect the awaiter or the worker's exit state

---

### Tracking with ProcessTask

`ProcessTask` carries the full execution story. You can inspect it at any point after the task completes:

```python
async def main():
    task = asyncio.to_process(process_batch, records)

    try:
        result = await task
    except Exception:
        pass  # handled below

    print(f"Repr      : {repr(task)}")     # <ProcessTask func='process_batch' status='done' pid=... duration=...s>
    print(f"Function  : {task.func_name}")
    print(f"Args      : {task.args}")
    print(f"Kwargs    : {task.kwargs}")
    print(f"PID       : {task.pid}")
    print(f"Status    : {task.status}")       # TaskStatus.DONE (== "done")
    print(f"Started   : {task.start_time}")   # monotonic float
    print(f"Ended     : {task.end_time}")
    print(f"Duration  : {task.duration:.4f}s")
    print(f"Exception : {task.exception}")    # None if successful
```

You can also collect tasks and inspect them in bulk:

```python
async def main():
    tasks = [asyncio.to_process(process_item, item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for task, result in zip(tasks, results):
        if task.status == "failed":
            print(f"{task.func_name} failed after {task.duration:.2f}s: {task.exception}")
        else:
            print(f"{task.func_name} completed in {task.duration:.2f}s → {result}")
```

---

### Handling Failures

If the worker function raises an exception, the `ProcessTask` captures it and re-raises it when awaited. The task's `status` becomes `"failed"` and `task.exception` holds the original exception:

```python
def risky_operation(x):
    if x < 0:
        raise ValueError(f"x must be non-negative, got {x}")
    return x ** 0.5

async def main():
    task = asyncio.to_process(risky_operation, -1)

    try:
        result = await task
    except ValueError as e:
        print(f"Task failed: {e}")
        print(f"Status    : {task.status}")     # TaskStatus.FAILED  (== "failed")
        print(f"Exception : {task.exception}")  # ValueError("x must be non-negative, got -1")
```

> **Note on pickling:** Arguments and return values are serialized across the process boundary using `pickle`. If your function, arguments, or return value cannot be pickled, the task will fail with a `PicklingError` — captured the same way.

---

### Cancellation

`ProcessTask.cancel()` is a proper override that actually stops the worker:

```python
async def main():
    task = asyncio.to_process(very_long_job, huge_dataset, cancel_timeout=5.0)

    # Cancel after 2 seconds
    await asyncio.sleep(2.0)
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        print(f"Task cancelled (status={task.status})")  # TaskStatus.CANCELLED (== "cancelled")
        print(f"Ran for {task.duration:.2f}s before cancellation")
```

**Cancellation sequence:**

1. If the worker PID is known: `SIGTERM` is sent to the process, giving it a chance to clean up
2. After `cancel_timeout` seconds: if the process is still alive, `SIGKILL` is sent
3. `CancelledError` is propagated to all awaiters
4. `task.status` is set to `"cancelled"`, and `task.end_time` / `task.duration` are recorded

If the task hasn't started yet (status is `"pending"`), only the asyncio cancellation is applied — no signals are needed.

> **Windows note:** Signal escalation (`SIGTERM`/`SIGKILL`) requires Unix. On Windows, calling `cancel()` with a known PID raises `NotImplementedError`. Pure asyncio cancellation (no PID yet) works on all platforms.

---

## API Reference

### `asyncio.to_process`

```python
asyncio.to_process(
    func: Callable,
    /,
    *args: Any,
    executor: ProcessPoolExecutor | None = None,
    cancel_timeout: float = 5.0,
    timeout: float | None = None,
    on_start: Callable[[ProcessTask], None] | None = None,
    on_done: Callable[[ProcessTask], None] | None = None,
    on_error: Callable[[ProcessTask], None] | None = None,
    **kwargs: Any,
) -> ProcessTask
```

Dispatches `func(*args, **kwargs)` to a separate process and returns an awaitable `ProcessTask`.

**Must be called from within a running asyncio event loop** (i.e., inside a coroutine). Raises `RuntimeError` if called outside a running loop.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `func` | `Callable` | — | The function to run in a worker process. Must be picklable (top-level or importable). |
| `*args` | `Any` | — | Positional arguments passed to `func`. Must be picklable. |
| `executor` | `ProcessPoolExecutor \| None` | `None` | Executor to use. Falls back to the module default, then Python's default pool. |
| `cancel_timeout` | `float` | `5.0` | Seconds between SIGTERM and SIGKILL on cancellation. |
| `timeout` | `float \| None` | `None` | Wall-clock seconds before the worker is forcibly cancelled. `None` = no limit. |
| `on_start` | `Callable[[ProcessTask], None] \| None` | `None` | Called when the task transitions to `RUNNING`. |
| `on_done` | `Callable[[ProcessTask], None] \| None` | `None` | Called when the task completes successfully. |
| `on_error` | `Callable[[ProcessTask], None] \| None` | `None` | Called when the task fails or times out. |
| `**kwargs` | `Any` | — | Keyword arguments passed to `func`. Must be picklable. |

---

### `loop.to_process`

```python
loop.to_process(
    func: Callable,
    /,
    *args: Any,
    executor: ProcessPoolExecutor | None = None,
    cancel_timeout: float = 5.0,
    timeout: float | None = None,
    on_start: Callable[[ProcessTask], None] | None = None,
    on_done: Callable[[ProcessTask], None] | None = None,
    on_error: Callable[[ProcessTask], None] | None = None,
    **kwargs: Any,
) -> ProcessTask
```

Identical to `asyncio.to_process` but called on a specific event loop instance:

```python
loop = asyncio.get_event_loop()
task = loop.to_process(fn, *args, **kwargs)
```

---

### `ProcessTask`

`ProcessTask` is a subclass of `asyncio.Task`. It is returned by both `asyncio.to_process` and `loop.to_process`. Import it for type annotations and `isinstance` checks:

```python
from async_patcher import ProcessTask
```

#### Attributes

| Attribute | Type | Description |
|---|---|---|
| `pid` | `int \| None` | PID of the worker process. `None` until the process starts. |
| `func_name` | `str` | `func.__name__` — name of the submitted callable. |
| `args` | `tuple` | Positional arguments passed to the callable. |
| `kwargs` | `dict` | Keyword arguments passed to the callable. |
| `start_time` | `float` | `time.monotonic()` recorded at task construction. |
| `end_time` | `float \| None` | `time.monotonic()` recorded on completion, failure, or cancellation. |
| `duration` | `float \| None` | `end_time - start_time`. Set at the same time as `end_time`. |
| `status` | `TaskStatus` | Current lifecycle state (see [`TaskStatus`](#taskstatus)). Also comparable to bare strings. |
| `exception` | `BaseException \| None` | The exception raised by the worker, if `status == "failed"`. |
| `cancel_timeout` | `float` | Seconds between SIGTERM and SIGKILL on cancellation. |

#### `__repr__`

```python
repr(task)
# <ProcessTask func='crunch_numbers' status='done' pid=84312 duration=0.0231s>
# <ProcessTask func='crunch_numbers' status='running' pid='n/a' duration='n/a'>
```

PID and duration show as `'n/a'` while the task is pending or running.

#### Status lifecycle

```
pending  →  running  →  done
                    ↘  failed
         ↘ cancelled     (cancel called before running)
                    ↘  cancelled  (cancel called while running)
```

#### Methods

`ProcessTask` inherits all `asyncio.Task` methods. The following are overridden:

**`cancel(msg=None) → bool`**

Sends SIGTERM to the worker process (if PID is known), schedules SIGKILL after `cancel_timeout` seconds, and calls `super().cancel()`. Raises `NotImplementedError` on Windows when a PID is already known.

---

### `TaskStatus`

`TaskStatus` is a `str`-mixin enum with members for each lifecycle state. Because it inherits `str`, existing code that compares `task.status == "done"` continues to work unchanged.

```python
from async_patcher import TaskStatus

print(TaskStatus.PENDING)    # TaskStatus.PENDING
print(TaskStatus.PENDING.value)  # "pending"

# String equality is preserved
assert TaskStatus.DONE == "done"
assert TaskStatus.FAILED == "failed"
```

| Member | Value |
|---|---|
| `TaskStatus.PENDING` | `"pending"` |
| `TaskStatus.RUNNING` | `"running"` |
| `TaskStatus.DONE` | `"done"` |
| `TaskStatus.FAILED` | `"failed"` |
| `TaskStatus.CANCELLED` | `"cancelled"` |

---

### `set_default_executor` / `get_default_executor`

```python
from async_patcher import set_default_executor, get_default_executor
from concurrent.futures import ProcessPoolExecutor

set_default_executor(ProcessPoolExecutor(max_workers=8))
pool = get_default_executor()   # ProcessPoolExecutor | None
```

`set_default_executor(None)` clears the default and falls back to Python's built-in pool.

---

### `process_pool`

```python
from async_patcher import process_pool

async with process_pool(max_workers: int = ...) as pool:
    ...
```

An async context manager that:
1. Creates a `ProcessPoolExecutor` with the given `max_workers`
2. Sets it as the module default (via `set_default_executor`)
3. On `__aexit__`: calls `executor.shutdown(wait=True)` and restores the previous default

---

### `run_in_process`

```python
from async_patcher import run_in_process

# Bare decorator — uses module default executor
@run_in_process
def my_fn(x: int) -> int: ...

# Parameterized decorator
@run_in_process(executor=pool, cancel_timeout=2.0)
def my_fn(x: int) -> int: ...
```

When the decorated function is called from a coroutine, it returns an awaitable `ProcessTask`. `functools.wraps` preserves `__name__` and `__doc__`.

---

### `__version__`

```python
import async_patcher
print(async_patcher.__version__)  # e.g. "0.2.0"
```

Read from `importlib.metadata` at import time; falls back to `"0.1.0"` for unpacked source trees.

---

## Typed Stubs & py.typed

`async-patcher` ships a `py.typed` marker and `.pyi` stub files for all public modules. Type checkers (`mypy`, `pyright`, `pylance`) discover them automatically — no extra configuration needed.

```
async_patcher/
├── py.typed          # PEP 561 marker
├── __init__.pyi
├── task.pyi
├── patch.pyi
├── decorators.pyi
└── pool.pyi
```

The package passes `mypy --strict` on all source files. To verify locally:

```bash
uv run mypy --strict async_patcher
# Success: no issues found in 5 source files
```

> **Known limitation:** `asyncio.to_process` is added by runtime monkey-patching and is invisible to the standard `asyncio` stubs. For full call-site type coverage, import the typed `ProcessTask` return value rather than relying on `asyncio.to_process` being typed by a type checker.

---

## How It Works

```
Your coroutine
     │
     │  asyncio.to_process(fn, *args, **kwargs)
     ▼
ProcessTask.__init__
  ├─ records func_name, args, kwargs, start_time
  ├─ wraps call as functools.partial(fn, *args, **kwargs)
  └─ schedules _run() coroutine as an asyncio.Task

ProcessTask._run()  (coroutine, runs on event loop)
  ├─ sets status = RUNNING  →  fires on_start callback
  ├─ opens multiprocessing.Pipe to capture worker PID eagerly
  ├─ await loop.run_in_executor(executor, _worker_wrapper_with_pid, partial_fn, pipe)
  │                                         │
  │            ┌────────────────────────────┘
  │            ▼
  │    _worker_wrapper_with_pid(partial_fn, pipe)   ← runs in worker process
  │      ├─ pid = os.getpid(); pipe.send(pid)       ← captured before work starts
  │      ├─ result = partial_fn()
  │      └─ return (pid, result)
  │
  ├─ unpacks (pid, result)
  ├─ sets self.pid, status = DONE, end_time, duration
  ├─ fires on_done callback
  └─ returns result to awaiter

On timeout:
  ├─ asyncio.wait_for raises TimeoutError
  ├─ os.kill(pid, SIGTERM)  →  SIGKILL after cancel_timeout
  ├─ status = FAILED
  └─ fires on_error callback

On cancel():
  ├─ os.kill(pid, SIGTERM)
  ├─ loop.call_later(cancel_timeout, _sigkill_if_alive, pid)
  └─ super().cancel() → CancelledError to awaiter

On exception in worker:
  ├─ status = FAILED
  ├─ self.exception = exc
  ├─ fires on_error callback
  └─ re-raises to awaiter
```

---

## Caveats & Limitations

**Arguments and return values must be picklable.**
`ProcessPoolExecutor` serializes everything across the process boundary using `pickle`. Lambda functions, closures, and objects without `__reduce__` will raise a `PicklingError`. Use top-level functions and plain data structures.

**Functions must be importable.**
Worker processes import your module to find the function. Functions defined interactively (e.g. in a REPL or Jupyter notebook) may not be importable and will cause `AttributeError` or `PicklingError`.

**The `if __name__ == "__main__":` guard is required on Windows.**
On Windows, Python uses `spawn` to create worker processes, which re-executes the module. Without the guard, your script runs again in each worker. On macOS/Linux (`fork`), this is less critical but still good practice.

```python
if __name__ == "__main__":
    asyncio.run(main())
```

**SIGTERM/SIGKILL and `cancel()` with a PID only work on Unix.**
On Windows, calling `cancel()` after a worker PID is known raises `NotImplementedError`. When the worker hasn't started yet (`pid is None`), pure asyncio cancellation is used and works on all platforms.

**`add_reader` may not be available on all event loops.**
The pipe-based eager PID capture uses `loop.add_reader`. On Windows with the Proactor event loop, this falls back to setting `pid` after the executor future resolves (the original behavior). Timeout cancellation in this fallback is best-effort.

**`asyncio.to_process` is not typed at the call site.**
Runtime monkey-patching is invisible to static type checkers. Assign the return value to `ProcessTask` for downstream type safety.

**Sync `with` on `process_pool` is not supported.**
Only `async with process_pool(...)` is supported.

**No cross-loop task tracking.**
`ProcessTask` instances are bound to the loop on which they were created. Do not share them across loops.

---

## Running Tests

```bash
# Clone the repo
git clone https://github.com/satyamsoni2211/async_patcher.git
cd async_patcher

# Install with dev dependencies (using uv — recommended)
uv sync --extra dev

# Or with pip
pip install -e ".[dev]"

# Run the full test suite (67 tests)
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_task.py -v
uv run pytest tests/test_callbacks.py -v

# Type-check the package
uv run mypy --strict async_patcher
```

### Test structure

| File | Tests | Focus |
|---|---|---|
| `tests/test_task.py` | 9 | `ProcessTask` construction, metadata, lifecycle, cancellation, exception capture, pickling |
| `tests/test_patch.py` | 7 | Patching `asyncio` + `BaseEventLoop`, idempotency, end-to-end `await`, kwargs, `RuntimeError` outside loop |
| `tests/test_task_status.py` | 7 | `TaskStatus` enum, str-mixin equality, status field type |
| `tests/test_version.py` | 4 | `__version__` exists, non-empty, matches semver pattern |
| `tests/test_windows_cancellation.py` | 3 | Windows `NotImplementedError`; no-PID path; Linux regression |
| `tests/test_default_executor.py` | 5 | Getter/setter; fallback; explicit-arg-wins |
| `tests/test_decorator.py` | 9 | Bare/empty/parameterized forms; metadata preservation |
| `tests/test_timeout.py` | 4 | `timeout` accepted; default `None`; `TimeoutError` raised; SIGTERM fires |
| `tests/test_process_pool.py` | 5 | `async with` lifecycle; default restored on exit; default used as executor |
| `tests/test_repr.py` | 6 | `__repr__` content (func, status, pid, duration) |
| `tests/test_callbacks.py` | 7 | `on_start`/`on_done`/`on_error` order and arguments |
| `tests/test_stub_smoke.py` | 1 | Subprocess `mypy --strict` on consumer code |
| **Total** | **67** | |

---

## Contributing

Contributions are welcome! Here's how to get started:

### 1. Fork and clone

```bash
git clone https://github.com/<your-username>/async_patcher.git
cd async_patcher
```

### 2. Set up your environment

```bash
uv sync --extra dev
```

### 3. Create a branch

```bash
git checkout -b feat/your-feature-name
```

### 4. Make your changes

- Follow the existing code style (PEP 8, type annotations)
- Write tests for any new behaviour — the project follows **TDD**
- Keep files focused: `task.py` owns `ProcessTask`, `patch.py` owns monkey-patching, `decorators.py` owns `@run_in_process`, `pool.py` owns `process_pool`
- Update `.pyi` stubs for any new public symbols
- `from __future__ import annotations` at the top of every module

### 5. Run tests and type checks

```bash
uv run pytest -v
uv run mypy --strict async_patcher
```

All 67 tests must pass and `mypy --strict` must report no issues before submitting.

### 6. Commit and push

```bash
git add .
git commit -m "feat: describe your change"
git push origin feat/your-feature-name
```

### 7. Open a Pull Request

Open a PR against `master` on [github.com/satyamsoni2211/async_patcher](https://github.com/satyamsoni2211/async_patcher). Include:
- A clear description of what the change does and why
- Any relevant issue numbers
- Test output confirming all tests pass and mypy is clean

### Reporting issues

Found a bug? Please [open an issue](https://github.com/satyamsoni2211/async_patcher/issues) with:
- Python version (`python --version`)
- OS and version
- Minimal reproducible example
- Full traceback

---

## License

MIT License — see [LICENSE](LICENSE) for details.

```
Copyright (c) 2026 Satyam Soni

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<p align="center">
  Made with ♥ by <a href="https://github.com/satyamsoni2211">Satyam Soni</a>
</p>
