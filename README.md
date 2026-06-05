# async-patcher

[![Python Version](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13%20|%203.14-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/satyamsoni2211/async_patcher/actions/workflows/ci.yml/badge.svg)](https://github.com/satyamsoni2211/async_patcher/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/satyamsoni2211/async_patcher/branch/main/graph/badge.svg)](https://codecov.io/gh/satyamsoni2211/async_patcher)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](#installation)

> Seamlessly offload CPU-bound work from your asyncio event loop to separate processes — with full tracking, rich metadata, and graceful cancellation.

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
  - [Custom Cancellation Timeout](#custom-cancellation-timeout)
  - [Tracking with ProcessTask](#tracking-with-processtask)
  - [Handling Failures](#handling-failures)
  - [Cancellation](#cancellation)
- [API Reference](#api-reference)
  - [asyncio.to_process](#asyncioto_process)
  - [loop.to_process](#loopto_process)
  - [ProcessTask](#processtask)
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

`async-patcher` solves all three:

```python
import async_patcher  # one import — asyncio is patched

task = asyncio.to_process(crunch_numbers, dataset)
result = await task

print(f"Done in {task.duration:.2f}s on PID {task.pid}")
```

---

## Features

- **Zero-friction patching** — just `import async_patcher`; no explicit setup calls needed
- **Dual access points** — `asyncio.to_process(...)` at module level, `loop.to_process(...)` inside coroutines
- **Rich `ProcessTask` object** — full metadata: PID, function name, args/kwargs, timing, status, exception
- **Proper `asyncio.Task` subclass** — awaitable, cancellable, compatible with `asyncio.gather`, `asyncio.wait`, `asyncio.shield`
- **Graceful cancellation** — SIGTERM first, then SIGKILL after a configurable timeout
- **kwargs support** — pass keyword arguments naturally; `functools.partial` handles the rest
- **Custom executor support** — bring your own `ProcessPoolExecutor` for fine-grained control
- **Idempotent patching** — importing `async_patcher` multiple times is safe
- **Zero runtime dependencies** — pure Python 3.11+ stdlib

---

## Requirements

- Python **3.11** or newer
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
    print(f"Status : {task.status}")       # "done"
    print(f"PID    : {task.pid}")          # e.g. 84312
    print(f"Took   : {task.duration:.3f}s")


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

> **Tip:** A shared, long-lived executor avoids the overhead of spawning new processes on every call. Create it once at startup and reuse it across your application.

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

### Tracking with ProcessTask

`ProcessTask` carries the full execution story. You can inspect it at any point after the task completes:

```python
async def main():
    task = asyncio.to_process(process_batch, records)

    try:
        result = await task
    except Exception:
        pass  # handled below

    print(f"Function  : {task.func_name}")
    print(f"Args      : {task.args}")
    print(f"Kwargs    : {task.kwargs}")
    print(f"PID       : {task.pid}")
    print(f"Status    : {task.status}")       # done | failed | cancelled
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
        print(f"Status    : {task.status}")     # "failed"
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
        print(f"Task cancelled (status={task.status})")  # "cancelled"
        print(f"Ran for {task.duration:.2f}s before cancellation")
```

**Cancellation sequence:**

1. If the worker PID is known: `SIGTERM` is sent to the process, giving it a chance to clean up
2. After `cancel_timeout` seconds: if the process is still alive, `SIGKILL` is sent
3. `CancelledError` is propagated to all awaiters
4. `task.status` is set to `"cancelled"`, and `task.end_time` / `task.duration` are recorded

If the task hasn't started yet (status is `"pending"`), only the asyncio cancellation is applied — no signals are needed.

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
    **kwargs: Any,
) -> ProcessTask
```

Dispatches `func(*args, **kwargs)` to a separate process and returns an awaitable `ProcessTask`.

**Must be called from within a running asyncio event loop** (i.e., inside a coroutine). Raises `RuntimeError` if called outside a running loop.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `func` | `Callable` | — | The function to run in a worker process. Must be picklable (top-level or importable). |
| `*args` | `Any` | — | Positional arguments passed to `func`. Must be picklable. |
| `executor` | `ProcessPoolExecutor \| None` | `None` | Executor to use. If `None`, Python's default pool is used. |
| `cancel_timeout` | `float` | `5.0` | Seconds between SIGTERM and SIGKILL on cancellation. |
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
    **kwargs: Any,
) -> ProcessTask
```

Identical to `asyncio.to_process` but called on a specific event loop instance. Useful when you have an explicit reference to the loop:

```python
loop = asyncio.get_event_loop()
task = loop.to_process(fn, *args, **kwargs)
```

---

### `ProcessTask`

`ProcessTask` is a subclass of `asyncio.Task`. It is returned by both `asyncio.to_process` and `loop.to_process`. You can import it for type annotations and `isinstance` checks:

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
| `status` | `str` | One of `"pending"`, `"running"`, `"done"`, `"failed"`, `"cancelled"`. |
| `exception` | `BaseException \| None` | The exception raised by the worker, if `status == "failed"`. |
| `cancel_timeout` | `float` | Seconds between SIGTERM and SIGKILL on cancellation. |

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

Sends SIGTERM to the worker process (if PID is known), schedules SIGKILL after `cancel_timeout` seconds, and calls `super().cancel()`. Sets `status = "cancelled"` if the task was still pending.

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
  ├─ sets status = "running"
  ├─ await loop.run_in_executor(executor, _worker_wrapper, partial_fn)
  │                                         │
  │            ┌────────────────────────────┘
  │            ▼
  │    _worker_wrapper(partial_fn)   ← runs in worker process
  │      ├─ pid = os.getpid()
  │      ├─ result = partial_fn()
  │      └─ return (pid, result)
  │
  ├─ unpacks (pid, result)
  ├─ sets self.pid, status = "done"
  └─ returns result to awaiter

On cancel():
  ├─ os.kill(pid, SIGTERM)
  ├─ loop.call_later(cancel_timeout, _sigkill_if_alive, pid)
  └─ super().cancel() → CancelledError to awaiter

On exception in worker:
  ├─ status = "failed"
  ├─ self.exception = exc
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

**SIGTERM/SIGKILL only works on Unix.**
The cancellation escalation uses `os.kill` with `SIGTERM`/`SIGKILL`, which is Unix-only. On Windows, cancellation falls back to `super().cancel()` only (the process is not explicitly killed).

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

# Run the test suite
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_task.py -v
uv run pytest tests/test_patch.py -v
```

### Test structure

| File | What it tests |
|---|---|
| `tests/test_task.py` | `ProcessTask` construction, metadata, lifecycle transitions, cancellation, exception capture, pickling errors |
| `tests/test_patch.py` | Patching `asyncio` module and `BaseEventLoop`, idempotency, end-to-end `await`, kwargs, `RuntimeError` outside loop |

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

- Follow the existing code style (PEP 8, type annotations, docstrings)
- Write tests for any new behaviour — the project follows **TDD**
- Keep files focused: `task.py` owns `ProcessTask`, `patch.py` owns the monkey-patching

### 5. Run the tests

```bash
uv run pytest -v
```

All 16 tests must pass before submitting.

### 6. Commit and push

```bash
git add .
git commit -m "feat: describe your change"
git push origin feat/your-feature-name
```

### 7. Open a Pull Request

Open a PR against `main` on [github.com/satyamsoni2211/async_patcher](https://github.com/satyamsoni2211/async_patcher). Include:
- A clear description of what the change does and why
- Any relevant issue numbers
- Test output confirming all tests pass

### Code style

- Python 3.11+ syntax and type hints throughout
- `from __future__ import annotations` at the top of every module
- Docstrings on all public classes and methods
- No third-party runtime dependencies — stdlib only

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
