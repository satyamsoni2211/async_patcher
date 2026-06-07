"""Tests for the @run_in_process decorator."""
import asyncio
from concurrent.futures import ProcessPoolExecutor

import pytest

import async_patcher
from async_patcher import ProcessTask, run_in_process


def double(x):
    return x * 2


def _executor_target(x, y):
    return x + y


@pytest.mark.asyncio
async def test_decorator_no_parens_dispatches_to_process():
    @run_in_process
    def square(n):
        return n * n

    result = await square(7)
    assert result == 49


@pytest.mark.asyncio
async def test_decorator_empty_parens_dispatches_to_process():
    @run_in_process()
    def cube(n):
        return n ** 3

    result = await cube(3)
    assert result == 27


@pytest.mark.asyncio
async def test_decorator_call_returns_processtask():
    @run_in_process
    def add(x, y):
        return x + y

    obj = add(2, 3)
    assert isinstance(obj, ProcessTask)
    assert await obj == 5


@pytest.mark.asyncio
async def test_decorator_passes_executor():
    ex = ProcessPoolExecutor(max_workers=1)
    try:
        decorated = run_in_process(executor=ex)(_executor_target)
        task = decorated(10, 20)
        assert task._executor is ex
        assert await task == 30
    finally:
        ex.shutdown(wait=True)


@pytest.mark.asyncio
async def test_decorator_passes_cancel_timeout():
    @run_in_process(cancel_timeout=2.5)
    def add(x, y):
        return x + y

    task = add(1, 2)
    assert task.cancel_timeout == 2.5
    assert await task == 3


@pytest.mark.asyncio
async def test_decorator_propagates_kwargs():
    @run_in_process
    def power(base, exp):
        return base ** exp

    result = await power(2, exp=8)
    assert result == 256


@pytest.mark.asyncio
async def test_decorator_propagates_exceptions():
    @run_in_process
    def boom():
        raise ValueError("kaboom")

    with pytest.raises(ValueError, match="kaboom"):
        await boom()


def test_decorator_preserves_metadata():
    @run_in_process
    def my_special_function(x):
        """My docstring."""
        return x

    assert my_special_function.__name__ == "my_special_function"
    assert "My docstring." in (my_special_function.__doc__ or "")


def test_run_in_process_is_exposed_on_package():
    assert hasattr(async_patcher, "run_in_process")
    assert callable(async_patcher.run_in_process)
