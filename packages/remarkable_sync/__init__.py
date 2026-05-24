"""reMarkable sync adapters for generated HabitOS PDFs."""

from packages.remarkable_sync.base import (
    MACHINE_ROOT_FOLDER,
    RemarkableDocument,
    RemarkableSyncAdapter,
    SyncRequest,
    SyncResult,
    build_machine_owned_target,
)
from packages.remarkable_sync.manual import ManualRemarkableSyncAdapter

__all__ = [
    "MACHINE_ROOT_FOLDER",
    "ManualRemarkableSyncAdapter",
    "RemarkableDocument",
    "RemarkableSyncAdapter",
    "SyncRequest",
    "SyncResult",
    "build_machine_owned_target",
]
