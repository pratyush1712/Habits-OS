"""Lifecycle helpers for machine-owned reMarkable dashboard documents."""

from __future__ import annotations

from pathlib import Path

from packages.remarkable_sync import (
    CURRENT_DOCUMENT_NAME,
    ManualRemarkableSyncAdapter,
    RemarkableSyncAdapter,
    SyncRequest,
    SyncResult,
    build_archive_month_target,
    build_current_month_target,
)


class RemarkableLifecycleService:
    """Own naming and target preparation for current/archive dashboard PDFs."""

    def __init__(
        self,
        *,
        adapter: RemarkableSyncAdapter | None = None,
        output_dir: Path,
    ) -> None:
        self.adapter = adapter or ManualRemarkableSyncAdapter()
        self.output_dir = output_dir

    def get_current_document_name(self, month: str) -> str:
        return build_current_month_target(month).document_name

    def get_archive_document_name(self, month: str) -> str:
        return build_archive_month_target(month).document_name

    def get_current_target_path(self, month: str) -> str:
        return build_current_month_target(month).display_path

    def get_archive_target_path(self, month: str) -> str:
        return build_archive_month_target(month).display_path

    async def prepare_current_month_upload(
        self,
        month: str,
        pdf_path: Path,
        dry_run: bool,
    ) -> SyncResult:
        target = build_current_month_target(month)
        request = SyncRequest(
            local_pdf_path=pdf_path,
            document_name=target.document_name,
            folder_path=target.folder_path,
            dry_run=dry_run,
        )
        return await self.adapter.upload_pdf(request)

    async def prepare_archive_previous_month(
        self,
        month: str,
        dry_run: bool,
    ) -> SyncResult:
        target = build_archive_month_target(month)
        # Download the existing on-device document (with all its .rm annotations),
        # and re-upload it to the archive folder. This preserves handwritten notes
        # instead of uploading a fresh PDF that would lose all ink.
        return await self.adapter.archive_device_document(
            source_document_name=CURRENT_DOCUMENT_NAME,
            target_folder_path=target.folder_path,
            target_document_name=target.document_name,
            dry_run=dry_run,
        )
