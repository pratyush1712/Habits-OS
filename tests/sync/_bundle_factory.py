"""Builders for synthetic reMarkable artifacts used by sync tests.

Leading underscore so pytest does not collect it as a test module.
"""

from __future__ import annotations

import json
import uuid
import zipfile
from pathlib import Path

from pypdf import PdfWriter


def make_pdf(path: Path, n_pages: int) -> Path:
    """Write an ``n_pages`` blank PDF sized roughly like the reMarkable page."""

    writer = PdfWriter()
    for _ in range(n_pages):
        writer.add_blank_page(width=445, height=595)
    with open(path, "wb") as fh:
        writer.write(fh)
    return path


def make_rmdoc(
    path: Path,
    *,
    doc_id: str = "doc-1",
    n_pages: int = 3,
    rm_count: int = 0,
) -> tuple[Path, list[str]]:
    """Write a minimal ``.rmdoc`` bundle and return (path, page_uuids).

    ``rm_count`` synthetic ``<doc_id>/<pageUUID>.rm`` blobs are added to mimic
    handwritten ink anchored to the first pages.
    """

    page_uuids = [str(uuid.uuid4()) for _ in range(n_pages)]
    content = {
        "fileType": "pdf",
        "formatVersion": 1,
        "pageCount": n_pages,
        "pages": page_uuids,
        "redirectionPageMap": list(range(n_pages)),
    }
    base = path.parent / f"_{doc_id}_base.pdf"
    make_pdf(base, n_pages)
    pdf_bytes = base.read_bytes()
    base.unlink()

    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr(f"{doc_id}.content", json.dumps(content))
        zf.writestr(
            f"{doc_id}.metadata",
            json.dumps({"visibleName": doc_id, "type": "DocumentType"}),
        )
        zf.writestr(f"{doc_id}.pagedata", "Blank\n" * n_pages)
        zf.writestr(f"{doc_id}.pdf", pdf_bytes)
        for i in range(rm_count):
            zf.writestr(
                f"{doc_id}/{page_uuids[i]}.rm",
                b"reMarkable .lines fake ink " + bytes([i % 256]),
            )
    return path, page_uuids
