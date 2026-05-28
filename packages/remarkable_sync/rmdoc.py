"""Read and rewrite reMarkable ``.rmdoc`` bundles.

An ``.rmdoc`` is the zip archive that ``rmapi get`` produces for a document.
For a PDF-backed document it contains, at the archive root:

    <docId>.content    JSON: page UUID list, pageCount, redirectionPageMap, ...
    <docId>.metadata   JSON: visibleName, lastModified, ...
    <docId>.pagedata    per-page template names
    <docId>.pdf         the base PDF (the "data layer")

and, once the user has written on it, the ink layer as additional blobs keyed
to the page UUIDs in ``.content`` (e.g. ``<docId>/<pageUUID>.rm``).

This module swaps **only** the base PDF blob, leaving ``.content`` (and thus the
page UUIDs every ink stroke is anchored to) and all annotation blobs untouched.
That is what lets HabitOS refresh the dashboard data daily without discarding
handwritten annotations -- provided the freshly rendered PDF is *page-stable*
(same page count/order as what is already on the device). The page-count guard
below enforces that invariant; a mismatch raises rather than risk misplacing
ink.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


class PageCountMismatch(ValueError):
    """Raised when a replacement PDF would change the document's page count."""

    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"refusing to swap base PDF: device document has {expected} pages "
            f"but the rendered PDF has {actual}. Swapping would misplace "
            "annotations. Re-render a page-stable PDF or reset the document."
        )


class MalformedBundle(ValueError):
    """Raised when an .rmdoc does not contain exactly one base PDF / .content."""


@dataclass(frozen=True)
class SwapInfo:
    doc_id: str
    page_count: int
    rm_file_count: int


def _root_entry(names: list[str], suffix: str) -> str:
    matches = [n for n in names if n.endswith(suffix) and "/" not in n]
    if len(matches) != 1:
        raise MalformedBundle(
            f"expected exactly one root '{suffix}' entry, found {matches!r}"
        )
    return matches[0]


def count_pdf_pages(pdf_path: Path) -> int:
    return len(PdfReader(str(pdf_path)).pages)


def read_page_count(rmdoc_path: Path) -> int:
    """Return the ``pageCount`` recorded in the bundle's ``.content``."""

    with zipfile.ZipFile(rmdoc_path) as zf:
        content_name = _root_entry(zf.namelist(), ".content")
        content = json.loads(zf.read(content_name))
    return int(content["pageCount"])


def swap_base_pdf(src_rmdoc: Path, new_pdf: Path, dst_rmdoc: Path) -> SwapInfo:
    """Write ``dst_rmdoc`` = ``src_rmdoc`` with only its base PDF replaced.

    Every other archive member -- ``.content``, ``.pagedata``, ``.metadata`` and
    every annotation blob -- is copied byte-for-byte, so page UUIDs and ink are
    preserved. Raises :class:`PageCountMismatch` if ``new_pdf`` does not have the
    same number of pages as the bundle records, and never writes ``dst_rmdoc`` in
    that case.
    """

    with zipfile.ZipFile(src_rmdoc) as zf:
        names = zf.namelist()
        pdf_name = _root_entry(names, ".pdf")
        content_name = _root_entry(names, ".content")
        content = json.loads(zf.read(content_name))
        expected = int(content["pageCount"])

        actual = count_pdf_pages(new_pdf)
        if actual != expected:
            raise PageCountMismatch(expected, actual)

        doc_id = pdf_name[: -len(".pdf")]
        rm_count = sum(1 for n in names if n.endswith(".rm"))
        new_pdf_bytes = new_pdf.read_bytes()

        dst_rmdoc.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dst_rmdoc, "w", zipfile.ZIP_STORED) as out:
            for info in zf.infolist():
                data = new_pdf_bytes if info.filename == pdf_name else zf.read(info.filename)
                out.writestr(info, data)

    return SwapInfo(doc_id=doc_id, page_count=expected, rm_file_count=rm_count)


__all__ = [
    "MalformedBundle",
    "PageCountMismatch",
    "SwapInfo",
    "count_pdf_pages",
    "read_page_count",
    "swap_base_pdf",
]
