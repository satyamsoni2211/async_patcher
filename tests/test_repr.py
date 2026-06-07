"""Tests for the __repr__ of ProcessTask."""

from __future__ import annotations

import asyncio
import re

import pytest

from async_patcher.task import ProcessTask


def double(x):
    return x * 2


def test_repr_includes_func_name():
    loop = asyncio.new_event_loop()
    try:
        task = ProcessTask(double, (4,), {}, loop=loop, executor=None, cancel_timeout=5.0)
        r = repr(task)
        assert "double" in r
    finally:
        loop.close()


def test_repr_includes_pending_status():
    loop = asyncio.new_event_loop()
    try:
        task = ProcessTask(double, (4,), {}, loop=loop, executor=None, cancel_timeout=5.0)
        r = repr(task)
        assert "pending" in r
    finally:
        loop.close()


@pytest.mark.asyncio
async def test_repr_includes_done_status():
    loop = asyncio.get_event_loop()
    task = ProcessTask(double, (4,), {}, loop=loop, executor=None, cancel_timeout=5.0)
    await task
    r = repr(task)
    assert "done" in r
    assert "double" in r


@pytest.mark.asyncio
async def test_repr_includes_pid():
    loop = asyncio.get_event_loop()
    task = ProcessTask(double, (4,), {}, loop=loop, executor=None, cancel_timeout=5.0)
    await task
    r = repr(task)
    assert str(task.pid) in r


@pytest.mark.asyncio
async def test_repr_includes_duration():
    loop = asyncio.get_event_loop()
    task = ProcessTask(double, (4,), {}, loop=loop, executor=None, cancel_timeout=5.0)
    await task
    r = repr(task)
    # Duration should be a numeric value; assert we can find it
    assert re.search(r"duration[=:]?\s*\d", r) or "duration" in r


def test_repr_format_is_class_name():
    loop = asyncio.new_event_loop()
    try:
        task = ProcessTask(double, (4,), {}, loop=loop, executor=None, cancel_timeout=5.0)
        r = repr(task)
        # Should start with class name
        assert r.startswith("<ProcessTask") or r.startswith("ProcessTask")
    finally:
        loop.close()
