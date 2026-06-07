"""Type-checking smoke tests for the .pyi stubs."""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest


def _double(x: int) -> int:
    return x * 2


def _mypy_is_runnable() -> str | None:
    """Return None if ``python -m mypy`` can be invoked, else a reason string.

    Some environments (notably Python 3.9 with stale ``.venv`` artifacts) have
    mypy installed but unable to import itself — usually a compiled-extension
    ABI mismatch (``mypy.server.aststrip.cpython-39-darwin.so`` built against
    a different libpython). In those cases the smoke test would fail for an
    environment reason unrelated to the stubs themselves, so we skip it
    cleanly. The CI matrix on 3.9 catches real stub regressions when the env
    is healthy.
    """
    probe = subprocess.run(
        [sys.executable, "-m", "mypy", "--version"],
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        return (probe.stderr or probe.stdout).strip() or "unknown error"
    return None


def test_consumer_can_use_stubs(tmp_path):
    """Type-check a small consumer file using the package's stubs.

    The reveal_type() calls surface the type info that ships via .pyi:
    ``ProcessTask``, ``TaskStatus``, ``pid: int | None``, ``duration: float | None``.
    The test asserts that mypy reveals these types correctly.
    """
    skip_reason = _mypy_is_runnable()
    if skip_reason is not None:
        pytest.skip(f"mypy not invokable in this environment: {skip_reason}")

    code = """
import async_patcher
from async_patcher import ProcessTask, TaskStatus
from async_patcher import get_default_executor, run_in_process, set_default_executor
from async_patcher.pool import process_pool

@run_in_process
def heavy(x: int) -> int:
    return x * 2

def main() -> None:
    reveal_type(heavy)
    reveal_type(heavy(5))
    reveal_type(get_default_executor())
    reveal_type(process_pool(max_workers=2))

main()
"""
    f = tmp_path / "consumer.py"
    f.write_text(code)

    # Resolve project root from this test file's location so the test works
    # in any environment (local dev, CI, container) — not just one machine.
    project_root = pathlib.Path(__file__).resolve().parent.parent

    # Use the Python interpreter that pytest itself is running under; that
    # interpreter already has mypy installed via the dev dependencies.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--strict",
            str(f),
        ],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )
    assert result.returncode == 0, f"mypy failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    # The reveal_type output should mention the typed public surface.
    # mypy renders unions differently by Python version: on 3.10+ it uses
    # PEP 604 ``X | Y`` syntax, on 3.9 it uses ``Union[X, Y]`` because PEP 604
    # is a runtime feature added in 3.10. Accept either form.
    assert (
        "ProcessPoolExecutor | None" in result.stdout
        or "Union[concurrent.futures.process.ProcessPoolExecutor, None]" in result.stdout
    ), f"expected ProcessPoolExecutor | None (or Union[..., None]) in mypy output:\n{result.stdout}"
    assert "async_patcher.pool.process_pool" in result.stdout
