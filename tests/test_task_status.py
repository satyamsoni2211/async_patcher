"""Tests for the TaskStatus enum."""

from __future__ import annotations

import asyncio
from enum import Enum

import pytest

from async_patcher.task import ProcessTask, TaskStatus


def test_task_status_is_an_enum():
    assert issubclass(TaskStatus, Enum)


def test_task_status_members_exist():
    expected = {"PENDING", "RUNNING", "DONE", "FAILED", "CANCELLED"}
    actual = {member.name for member in TaskStatus}
    assert actual == expected


def test_task_status_values_are_lowercase_strings():
    """str mixin keeps backward-compatible lowercase values."""
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.RUNNING.value == "running"
    assert TaskStatus.DONE.value == "done"
    assert TaskStatus.FAILED.value == "failed"
    assert TaskStatus.CANCELLED.value == "cancelled"


def test_task_status_equality_with_bare_string():
    """Backward-compat: task.status == 'done' must still work."""
    assert TaskStatus.DONE == "done"
    assert TaskStatus.FAILED == "failed"
    assert TaskStatus.CANCELLED == "cancelled"


def double(x):
    return x * 2


@pytest.mark.asyncio
async def test_process_task_status_is_taskstatus_instance():
    loop = asyncio.get_event_loop()
    task = ProcessTask(double, (4,), {}, loop=loop, executor=None, cancel_timeout=5.0)
    assert isinstance(task.status, TaskStatus)
    assert task.status is TaskStatus.PENDING
    _ = await task
    assert task.status is TaskStatus.DONE
    assert task.status == "done"  # str-mixin equality


@pytest.mark.asyncio
async def test_process_task_failed_status_is_taskstatus():
    def boom():
        raise RuntimeError("nope")

    loop = asyncio.get_event_loop()
    task = ProcessTask(boom, (), {}, loop=loop, executor=None, cancel_timeout=5.0)
    with pytest.raises(RuntimeError):
        await task
    assert task.status is TaskStatus.FAILED
    assert task.status == "failed"


@pytest.mark.asyncio
async def test_process_task_cancelled_status_is_taskstatus():
    def slow():
        import time

        time.sleep(10)

    loop = asyncio.get_event_loop()
    task = ProcessTask(slow, (), {}, loop=loop, executor=None, cancel_timeout=0.1)
    await asyncio.sleep(0.2)
    task.pid = 12345  # pretend it has a pid for the signal path
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass
    assert task.status is TaskStatus.CANCELLED
    assert task.status == "cancelled"
