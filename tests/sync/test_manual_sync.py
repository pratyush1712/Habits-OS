from __future__ import annotations

import pytest

from packages.remarkable_sync import (
    ManualRemarkableSyncAdapter,
    SyncRequest,
    build_archive_month_target,
    build_current_month_target,
)


def test_current_month_target_naming():
    target = build_current_month_target("2026-05")

    assert target.folder_path == ("HabitOS", "00 Current")
    assert target.document_name == "00 Current Month - 2026-05 Habit Dashboard"
    assert target.filename == "00 Current Month - 2026-05 Habit Dashboard.pdf"
    assert (
        target.display_path
        == "HabitOS/00 Current/00 Current Month - 2026-05 Habit Dashboard.pdf"
    )


def test_archive_month_target_naming():
    target = build_archive_month_target("2026-05")

    assert target.folder_path == ("HabitOS", "2026", "Archive")
    assert target.document_name == "2026-05 Habit Dashboard"
    assert target.filename == "2026-05 Habit Dashboard.pdf"
    assert target.display_path == "HabitOS/2026/Archive/2026-05 Habit Dashboard.pdf"


@pytest.mark.asyncio
async def test_manual_upload_returns_manual_required_instructions(tmp_path):
    pdf = tmp_path / "2026-05-habit-dashboard.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    target = build_current_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=pdf,
        document_name=target.document_name,
        folder_path=target.folder_path,
        dry_run=True,
    )

    result = await ManualRemarkableSyncAdapter().upload_pdf(request)

    assert result.adapter == "manual"
    assert result.action == "upload"
    assert result.status == "manual_required"
    assert result.device_mutated is False
    assert (
        result.target_path
        == "HabitOS/00 Current/00 Current Month - 2026-05 Habit Dashboard.pdf"
    )
    assert result.local_pdf_path == pdf
    assert any("http://10.11.99.1" in step for step in result.instructions)
    assert any("Do not replace unrelated handwritten notebooks" in step for step in result.instructions)


@pytest.mark.asyncio
async def test_manual_upload_reports_missing_pdf(tmp_path):
    target = build_current_month_target("2026-05")
    request = SyncRequest(
        local_pdf_path=tmp_path / "missing.pdf",
        document_name=target.document_name,
        folder_path=target.folder_path,
    )

    result = await ManualRemarkableSyncAdapter().upload_pdf(request)

    assert result.status == "not_configured"
    assert "does not exist" in result.message


@pytest.mark.asyncio
async def test_manual_list_documents_is_unsupported():
    with pytest.raises(NotImplementedError):
        await ManualRemarkableSyncAdapter().list_documents()
