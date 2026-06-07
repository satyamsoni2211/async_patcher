"""Tests for module-level default executor management."""
import asyncio
from concurrent.futures import ProcessPoolExecutor

import pytest

import async_patcher


@pytest.fixture(autouse=True)
def _reset_default_executor():
    """Snapshot the default executor and restore it after each test."""
    saved = async_patcher.get_default_executor()
    async_patcher.set_default_executor(None)
    yield
    async_patcher.set_default_executor(saved)


def test_get_default_executor_is_none_initially():
    assert async_patcher.get_default_executor() is None


def test_set_default_executor_then_get_returns_it():
    ex = ProcessPoolExecutor(max_workers=2)
    try:
        async_patcher.set_default_executor(ex)
        assert async_patcher.get_default_executor() is ex
    finally:
        ex.shutdown(wait=True)


def test_set_default_executor_to_none_clears_it():
    ex = ProcessPoolExecutor(max_workers=2)
    async_patcher.set_default_executor(ex)
    async_patcher.set_default_executor(None)
    assert async_patcher.get_default_executor() is None
    ex.shutdown(wait=True)


def add(x, y):
    return x + y


@pytest.mark.asyncio
async def test_to_process_uses_module_default_when_no_executor_passed():
    """to_process() falls back to the module default executor."""
    import async_patcher.patch  # noqa: F401 — ensure patched

    ex = ProcessPoolExecutor(max_workers=2)
    async_patcher.set_default_executor(ex)
    try:
        task = asyncio.to_process(add, 3, 4)
        result = await task
        assert result == 7
        # The worker should have run in a real process — its pid should
        # not be the current process's pid.
        assert task.pid is not None
        assert task.pid != __import__("os").getpid()
    finally:
        ex.shutdown(wait=True)


@pytest.mark.asyncio
async def test_to_process_explicit_executor_overrides_module_default():
    """Explicit executor argument wins over the module default."""
    import async_patcher.patch  # noqa: F401

    default_ex = ProcessPoolExecutor(max_workers=1)
    explicit_ex = ProcessPoolExecutor(max_workers=1)
    async_patcher.set_default_executor(default_ex)
    try:
        task = asyncio.to_process(add, 5, 6, executor=explicit_ex)
        result = await task
        assert result == 11
        assert task._executor is explicit_ex
    finally:
        default_ex.shutdown(wait=True)
        explicit_ex.shutdown(wait=True)
