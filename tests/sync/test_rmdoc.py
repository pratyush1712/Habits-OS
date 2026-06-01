"""Unit tests for the .rmdoc bundle rewrite helper.

These run entirely on synthetic bundles -- no rmapi, no network, no real
reMarkable document.
"""

from __future__ import annotations

import zipfile

import pytest

from packages.remarkable_sync import rmdoc
from tests.sync._bundle_factory import make_pdf, make_rmdoc


def test_read_page_count(tmp_path):
    src, _ = make_rmdoc(tmp_path / "doc.rmdoc", n_pages=43)
    assert rmdoc.read_page_count(src) == 43


def test_swap_preserves_content_and_ink(tmp_path):
    src, uuids = make_rmdoc(tmp_path / "doc.rmdoc", doc_id="abc", n_pages=5, rm_count=3)
    new_pdf = make_pdf(tmp_path / "fresh.pdf", 5)
    out = tmp_path / "merged.rmdoc"

    info = rmdoc.swap_base_pdf(src, new_pdf, out)

    assert info.doc_id == "abc"
    assert info.page_count == 5
    assert info.rm_file_count == 3

    with zipfile.ZipFile(src) as a, zipfile.ZipFile(out) as b:
        assert a.namelist() == b.namelist()
        # The base PDF blob is the only thing that changed.
        for name in a.namelist():
            if name.endswith(".pdf"):
                assert b.read(name) == new_pdf.read_bytes()
            else:
                assert a.read(name) == b.read(name), name
        # All three ink blobs survived untouched.
        rm_entries = [n for n in b.namelist() if n.endswith(".rm")]
        assert len(rm_entries) == 3
        for uid in uuids[:3]:
            assert f"abc/{uid}.rm" in rm_entries


def test_page_count_mismatch_aborts_without_writing(tmp_path):
    src, _ = make_rmdoc(tmp_path / "doc.rmdoc", n_pages=5)
    wrong = make_pdf(tmp_path / "wrong.pdf", 4)
    out = tmp_path / "merged.rmdoc"

    with pytest.raises(rmdoc.PageCountMismatch) as exc:
        rmdoc.swap_base_pdf(src, wrong, out)

    assert exc.value.expected == 5
    assert exc.value.actual == 4
    assert not out.exists()


def test_malformed_bundle_without_pdf_raises(tmp_path):
    bad = tmp_path / "bad.rmdoc"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("doc.content", "{}")
    new_pdf = make_pdf(tmp_path / "fresh.pdf", 1)

    with pytest.raises(rmdoc.MalformedBundle):
        rmdoc.swap_base_pdf(bad, new_pdf, tmp_path / "out.rmdoc")


def test_read_visible_name(tmp_path):
    src, _ = make_rmdoc(tmp_path / "doc.rmdoc", doc_id="hello")
    assert rmdoc.read_visible_name(src) == "hello"


def test_copy_with_visible_name_renames_and_preserves_ink(tmp_path):
    src, uuids = make_rmdoc(tmp_path / "doc.rmdoc", doc_id="abc", n_pages=4, rm_count=2)
    out = tmp_path / "archived.rmdoc"

    doc_id = rmdoc.copy_with_visible_name(src, out, "2026-05 Habit Dashboard")

    assert doc_id == "abc"
    assert rmdoc.read_visible_name(out) == "2026-05 Habit Dashboard"
    # Everything except the metadata is byte-identical; ink survives.
    with zipfile.ZipFile(src) as a, zipfile.ZipFile(out) as b:
        assert a.namelist() == b.namelist()
        for name in a.namelist():
            if name.endswith(".metadata"):
                continue
            assert a.read(name) == b.read(name), name
        rm_entries = [n for n in b.namelist() if n.endswith(".rm")]
        assert len(rm_entries) == 2
        for uid in uuids[:2]:
            assert f"abc/{uid}.rm" in rm_entries
