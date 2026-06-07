from importlib.metadata import PackageNotFoundError, version as _pkg_version

from .task import ProcessTask, TaskStatus
from . import patch as _patch_module
from .decorators import run_in_process
from .patch import get_default_executor, set_default_executor
from .pool import process_pool

try:
    __version__ = _pkg_version("async-patcher")
except PackageNotFoundError:  # pragma: no cover — package not installed
    __version__ = "0.1.0"

_patch_module.patch()  # auto-patch asyncio on import

__all__ = [
    "ProcessTask",
    "TaskStatus",
    "__version__",
    "get_default_executor",
    "set_default_executor",
    "process_pool",
    "run_in_process",
]
