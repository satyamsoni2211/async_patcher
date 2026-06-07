"""Tests for the process_pool() context manager."""

from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor

import pytest

import async_patcher


def _add(x, y):
    return x + y


@pytest.fixture(autouse=True)
def _reset_default_executor():
    saved = async_patcher.get_default_executor()
    async_patcher.set_default_executor(None)
    yield
    async_patcher.set_default_executor(saved)


def test_process_pool_is_exposed_on_package():
    assert hasattr(async_patcher, "process_pool")
    assert callable(async_patcher.process_pool)


@pytest.mark.asyncio
async def test_process_pool_enter_creates_executor_and_sets_default():
    async with async_patcher.process_pool(max_workers=2) as pool:
        assert isinstance(pool, ProcessPoolExecutor)
        assert async_patcher.get_default_executor() is pool
    # On exit, default should be cleared
    assert async_patcher.get_default_executor() is None


@pytest.mark.asyncio
async def test_process_pool_exit_shuts_down_executor():
    async with async_patcher.process_pool(max_workers=1) as pool:
        executor_ref = pool
    # After exit, the executor should be shut down
    with pytest.raises(RuntimeError):
        executor_ref.submit(lambda: 1).result(timeout=2)


@pytest.mark.asyncio
async def test_to_process_inside_process_pool_uses_it_as_default():
    async with async_patcher.process_pool(max_workers=2) as pool:
        task = asyncio.to_process(_add, 3, 4)
        assert task._executor is pool
        assert await task == 7


@pytest.mark.asyncio
async def test_process_pool_restores_previous_default_on_exit():
    previous = ProcessPoolExecutor(max_workers=1)
    async_patcher.set_default_executor(previous)
    try:
        async with async_patcher.process_pool(max_workers=2):
            # Inside the block, default is the new pool
            assert async_patcher.get_default_executor() is not previous
        # After the block, the previous default is restored
        assert async_patcher.get_default_executor() is previous
    finally:
        previous.shutdown(wait=True)
