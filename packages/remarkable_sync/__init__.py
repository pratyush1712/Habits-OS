"""reMarkable sync adapters for generated HabitOS PDFs."""

from packages.remarkable_sync.base import (
    CURRENT_DOCUMENT_NAME,
    MACHINE_ROOT_FOLDER,
    RemarkableDocument,
    RemarkableSyncAdapter,
    SyncRequest,
    SyncResult,
    build_archive_month_target,
    build_current_month_target,
    build_machine_owned_target,
)
from packages.remarkable_sync.manual import ManualRemarkableSyncAdapter
from packages.remarkable_sync.rmapi import (
    AsyncioSubprocessRunner,
    CompletedRun,
    RmapiConfig,
    RmapiRemarkableSyncAdapter,
    SubprocessRunner,
)

__all__ = [
    "CURRENT_DOCUMENT_NAME",
    "MACHINE_ROOT_FOLDER",
    "AsyncioSubprocessRunner",
    "CompletedRun",
    "ManualRemarkableSyncAdapter",
    "RemarkableDocument",
    "RemarkableSyncAdapter",
    "RmapiConfig",
    "RmapiRemarkableSyncAdapter",
    "SubprocessRunner",
    "SyncRequest",
    "SyncResult",
    "build_archive_month_target",
    "build_current_month_target",
    "build_machine_owned_target",
]
