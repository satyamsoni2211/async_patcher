from .task import ProcessTask
from . import patch as _patch_module

_patch_module.patch()  # auto-patch asyncio on import

__all__ = ["ProcessTask"]
