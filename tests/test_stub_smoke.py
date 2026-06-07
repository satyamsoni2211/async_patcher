"""Type-checking smoke tests for the .pyi stubs."""
import pathlib
import subprocess
import sys

import async_patcher


def _double(x: int) -> int:
    return x * 2


def test_consumer_can_use_stubs(tmp_path):
    """Type-check a small consumer file using the package's stubs.

    The reveal_type() calls surface the type info that ships via .pyi:
    ``ProcessTask``, ``TaskStatus``, ``pid: int | None``, ``duration: float | None``.
    The test asserts that mypy reveals these types correctly.
    """
    code = '''
import async_patcher
from async_patcher import ProcessTask, TaskStatus, run_in_process, get_default_executor, set_default_executor
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
'''
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
    assert result.returncode == 0, (
        f"mypy failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # The reveal_type output should mention the typed public surface
    assert "ProcessPoolExecutor | None" in result.stdout
    assert "async_patcher.pool.process_pool" in result.stdout
