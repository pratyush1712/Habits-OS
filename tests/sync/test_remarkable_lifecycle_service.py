from __future__ import annotations

import pytest

from apps.api.services.remarkable_lifecycle import RemarkableLifecycleService
from packages.remarkable_sync import ManualRemarkableSyncAdapter


def test_lifecycle_service_returns_current_and_archive_paths(tmp_path):
    service = RemarkableLifecycleService(
        adapter=ManualRemarkableSyncAdapter(),
        output_dir=tmp_path,
    )

    assert (
        service.get_current_document_name("2026-06")
        == "01. Habit Tracker"
    )
    assert (
        service.get_current_target_path("2026-06")
        == "01. Habit Tracker.pdf"
    )
    assert service.get_archive_document_name("2026-05") == "2026-05 Habit Dashboard"
    assert service.get_archive_target_path("2026-05") == "HabitOS/2026/Archive/2026-05 Habit Dashboard.pdf"


@pytest.mark.asyncio
async def test_prepare_current_month_upload_is_manual_safe(tmp_path):
    pdf = tmp_path / "2026-06-habit-dashboard.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    service = RemarkableLifecycleService(
        adapter=ManualRemarkableSyncAdapter(),
        output_dir=tmp_path,
    )

    result = await service.prepare_current_month_upload("2026-06", pdf, dry_run=False)

    assert result.status == "manual_required"
    assert result.device_mutated is False
    assert result.target_path == "01. Habit Tracker.pdf"


@pytest.mark.asyncio
async def test_prepare_archive_previous_month_uses_archive_target(tmp_path):
    pdf = tmp_path / "2026-05-habit-dashboard.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    service = RemarkableLifecycleService(
        adapter=ManualRemarkableSyncAdapter(),
        output_dir=tmp_path,
    )

    result = await service.prepare_archive_previous_month("2026-05", dry_run=True)

    assert result.status == "manual_required"
    assert result.device_mutated is False
    assert result.target_path == "HabitOS/2026/Archive/2026-05 Habit Dashboard.pdf"
