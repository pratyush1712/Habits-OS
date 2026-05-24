"""Manual reMarkable sync adapter.

This adapter is intentionally non-mutating. It validates the generated PDF path
and returns clear upload instructions for the user.
"""

from __future__ import annotations

from packages.remarkable_sync.base import RemarkableDocument, SyncAction, SyncRequest, SyncResult


class ManualRemarkableSyncAdapter:
    name = "manual"

    async def upload_pdf(self, request: SyncRequest) -> SyncResult:
        return _manual_result(request, action="upload")

    async def update_pdf(self, request: SyncRequest) -> SyncResult:
        return _manual_result(request, action="update")

    async def list_documents(self) -> list[RemarkableDocument]:
        raise NotImplementedError("manual sync cannot list documents on the device")


def _manual_result(request: SyncRequest, *, action: SyncAction) -> SyncResult:
    pdf_path = request.local_pdf_path
    if not pdf_path.exists():
        return SyncResult(
            adapter=ManualRemarkableSyncAdapter.name,
            action=action,
            dry_run=request.dry_run,
            local_pdf_path=pdf_path,
            target_path=request.target_path,
            status="not_configured",
            message=f"Generated PDF does not exist: {pdf_path}",
            instructions=["Render the month first, then run sync again."],
        )
    if not pdf_path.is_file():
        return SyncResult(
            adapter=ManualRemarkableSyncAdapter.name,
            action=action,
            dry_run=request.dry_run,
            local_pdf_path=pdf_path,
            target_path=request.target_path,
            status="not_configured",
            message=f"Generated PDF path is not a file: {pdf_path}",
            instructions=["Render the month to a PDF file, then run sync again."],
        )

    return SyncResult(
        adapter=ManualRemarkableSyncAdapter.name,
        action=action,
        dry_run=request.dry_run,
        local_pdf_path=pdf_path,
        target_path=request.target_path,
        status="manual_required",
        device_mutated=False,
        message=(
            "Manual upload instructions generated. "
            "No files were modified on the reMarkable device."
        ),
        instructions=[
            f"Confirm the generated PDF exists locally: {pdf_path}",
            "On the reMarkable 2, open Settings → Storage and enable USB web interface.",
            "Connect the tablet to this computer with USB.",
            "Open http://10.11.99.1/ in a browser.",
            f"Use or create the machine-owned folder path: {' / '.join(request.folder_path)}.",
            f"Upload the PDF as: {request.document_name}.pdf",
            f"Expected target path: {request.target_path}",
            "Do not replace unrelated handwritten notebooks or user-owned documents.",
        ],
    )
