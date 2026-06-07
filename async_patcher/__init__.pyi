from __future__ import annotations

from .decorators import run_in_process as run_in_process
from .patch import (
    get_default_executor as get_default_executor,
    set_default_executor as set_default_executor,
)
from .pool import process_pool as process_pool
from .task import ProcessTask as ProcessTask, TaskStatus as TaskStatus

__version__: str
