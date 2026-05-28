"""reMarkable manual upload orchestration."""

from __future__ import annotations

from pathlib import Path

from packages.core.repositories import RenderJobsRepo
from packages.remarkable_sync import (
    ManualRemarkableSyncAdapter,
    RemarkableSyncAdapter,
    RmapiRemarkableSyncAdapter,
    SyncRequest,
    SyncResult,
    build_machine_owned_target,
)


class RemarkableSyncService:
    def __init__(
        self,
        jobs_repo: RenderJobsRepo,
        adapter: RemarkableSyncAdapter | None = None,
    ) -> None:
        self.jobs_repo = jobs_repo
        self.adapter = adapter or ManualRemarkableSyncAdapter()

    async def status(self) -> dict:
        latest = await self.jobs_repo.latest()
        mode = (
            "automated_cloud"
            if isinstance(self.adapter, RmapiRemarkableSyncAdapter)
            else "manual_upload"
        )
        payload: dict = {
            "configured": True,
            "adapter": self.adapter.name,
            "mode": mode,
            "dry_run_supported": True,
            "machine_owned_root": "HabitOS",
            "latest_render_job": latest.model_dump(mode="json") if latest else None,
            "safety": (
                "Uploads target only generated HabitOS PDFs on the device home screen "
                "as '01. Habit Tracker' or under HabitOS/YYYY/Archive."
            ),
        }
        if isinstance(self.adapter, RmapiRemarkableSyncAdapter):
            payload["rmapi"] = await self.adapter.diagnostics()
        return payload

    async def sync_latest_month(
        self,
        month: str,
        *,
        dry_run: bool = True,
        update: bool = False,
    ) -> SyncResult:
        job = await self.jobs_repo.latest_for_month(month)
        if job is None:
            raise ValueError(f"No render job found for {month}")
        if job.status != "completed":
            raise ValueError(f"Latest render job for {month} is {job.status}, not completed")
        if not job.output_path:
            raise ValueError(f"Latest render job for {month} has no output_path")

        target = build_machine_owned_target(month)
        request = SyncRequest(
            local_pdf_path=Path(job.output_path),
            document_name=target.document_name,
            folder_path=target.folder_path,
            dry_run=dry_run,
        )
        if update:
            return await self.adapter.update_pdf(request)
        return await self.adapter.upload_pdf(request)
