"""
tests/test_ingest_router.py — Tests for Stage 1: ingest_router.py

Ground truth established by probing the actual PDFs before writing these tests:

  docs/source/Orange_TermSheet.pdf
    Total pages : 1
    Page 1      : 2176 chars  → native

  docs/source/Sample Termsheets.pdf
    Total pages : 10
    Pages 1–10  : 1089–1211 chars each  → all native

IMPORTANT — No scanned pages exist in the available PDFs.
The "scanned page" tests use mock pdfplumber pages (text="" or text="3")
to exercise the threshold branch without needing a real scanned PDF.
This is explicitly documented here so future engineers know it is intentional,
not an oversight.

Coverage:
  1. Known native page from Orange_TermSheet.pdf → route="native".
  2. Synthetic scanned page (text length ≤ 50) → route="scanned".
  3. Full Orange_TermSheet.pdf → 1 page, 1 native, 0 scanned.
  4. Full Sample Termsheets.pdf → 10 pages, 10 native, 0 scanned.
  5. Short-text page (watermark / page-number style, ≤ 50 chars) →
     must NOT be misclassified as native — proves the threshold matters.
  6. Exactly-50-char page → "scanned" (boundary: threshold is STRICTLY >50).
  7. Exactly-51-char page → "native".
  8. Empty page (text=None from pdfplumber) → "scanned" (not a crash).
  9. Output is a list[PageManifest] — Pydantic model, not a raw dict.
 10. Invalid route value cannot be stored (model rejects it at construction).
 11. persist() writes valid JSON that round-trips back to list[PageManifest].
 12. FileNotFoundError on a non-existent PDF.
 13. count_by_route() returns correct counts.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from models.page_manifest import PageManifest
from stages.ingest_router import (
    TEXT_THRESHOLD,
    count_by_route,
    persist,
    route_pdf,
    run,
    _route_page,
)

# ---------------------------------------------------------------------------
# Paths to real PDFs
# ---------------------------------------------------------------------------

ORANGE_PDF    = Path("docs/source/Orange_TermSheet.pdf")
SAMPLE_PDF    = Path("docs/source/Sample Termsheets.pdf")


# ---------------------------------------------------------------------------
# Synthetic page factory
# ---------------------------------------------------------------------------

def _fake_page(text: str | None) -> MagicMock:
    """Return a MagicMock that mimics a pdfplumber page."""
    page = MagicMock()
    page.extract_text.return_value = text
    return page


# ---------------------------------------------------------------------------
# 1 & 2. _route_page unit tests (no PDF I/O)
# ---------------------------------------------------------------------------

class TestRoutePageUnit:
    def test_rich_text_routes_native(self):
        """A page with well above 50 chars must be native."""
        page = _fake_page("A" * 200)
        assert _route_page(page) == "native"

    def test_empty_text_routes_scanned(self):
        """pdfplumber returns None for fully rasterised pages."""
        page = _fake_page(None)
        assert _route_page(page) == "scanned"

    def test_empty_string_routes_scanned(self):
        page = _fake_page("")
        assert _route_page(page) == "scanned"

    def test_whitespace_only_routes_scanned(self):
        """Whitespace does not count — stripped length is 0."""
        page = _fake_page("   \n\t  ")
        assert _route_page(page) == "scanned"

    def test_short_text_watermark_routes_scanned(self):
        """
        A page number / watermark ("3" or "Page 3 of 10") must not be
        misclassified as native.  This is exactly why threshold is >50, not >0.
        """
        for short in ["3", "Page 3 of 10", "DRAFT", "Confidential", "x" * 50]:
            page = _fake_page(short)
            result = _route_page(page)
            assert result == "scanned", (
                f"Expected 'scanned' for text {short!r} (len={len(short.strip())}), "
                f"got {result!r}"
            )

    def test_exactly_threshold_routes_scanned(self):
        """Boundary: exactly TEXT_THRESHOLD chars → scanned (rule is STRICTLY >)."""
        page = _fake_page("x" * TEXT_THRESHOLD)
        assert _route_page(page) == "scanned"

    def test_one_above_threshold_routes_native(self):
        """Boundary: TEXT_THRESHOLD + 1 chars → native."""
        page = _fake_page("x" * (TEXT_THRESHOLD + 1))
        assert _route_page(page) == "native"

    def test_long_text_routes_native(self):
        """Typical WBCIS page has ~1000+ chars — well above threshold."""
        wbcis_text = "Annexure 3 Weather Based Crop Insurance Scheme :- 2019-20 " * 20
        page = _fake_page(wbcis_text)
        assert _route_page(page) == "native"


# ---------------------------------------------------------------------------
# 3. Real PDF: Orange_TermSheet.pdf — integration tests
# ---------------------------------------------------------------------------

class TestOrangePDF:
    """
    Integration tests against the real Orange_TermSheet.pdf.
    Ground truth: 1 page, 2176 chars, route=native.
    """

    @pytest.fixture(autouse=True)
    def require_pdf(self):
        if not ORANGE_PDF.exists():
            pytest.skip(f"PDF not found: {ORANGE_PDF}")

    def test_orange_page_1_is_native(self):
        """Known native page — 2176 chars of selectable WBCIS table text."""
        manifests = route_pdf(ORANGE_PDF)
        assert manifests[0].route == "native"
        assert manifests[0].page_no == 1

    def test_orange_total_page_count(self):
        manifests = route_pdf(ORANGE_PDF)
        assert len(manifests) == 1

    def test_orange_all_native(self):
        manifests = route_pdf(ORANGE_PDF)
        counts = count_by_route(manifests)
        assert counts["native"]  == 1
        assert counts["scanned"] == 0

    def test_orange_output_is_list_of_page_manifest(self):
        """Output must be Pydantic PageManifest objects, not raw dicts."""
        manifests = route_pdf(ORANGE_PDF)
        assert all(isinstance(m, PageManifest) for m in manifests)

    def test_orange_page_no_is_one_based(self):
        manifests = route_pdf(ORANGE_PDF)
        page_nos = [m.page_no for m in manifests]
        assert page_nos == list(range(1, len(manifests) + 1))


# ---------------------------------------------------------------------------
# 4. Real PDF: Sample Termsheets.pdf
# ---------------------------------------------------------------------------

class TestSamplePDF:
    """
    Integration tests against Sample Termsheets.pdf.
    Ground truth: 10 pages, all native (1089–1211 chars each).
    """

    @pytest.fixture(autouse=True)
    def require_pdf(self):
        if not SAMPLE_PDF.exists():
            pytest.skip(f"PDF not found: {SAMPLE_PDF}")

    def test_sample_total_page_count(self):
        manifests = route_pdf(SAMPLE_PDF)
        assert len(manifests) == 10

    def test_sample_all_native(self):
        manifests = route_pdf(SAMPLE_PDF)
        counts = count_by_route(manifests)
        assert counts["native"]  == 10
        assert counts["scanned"] == 0

    def test_sample_page_nos_sequential(self):
        manifests = route_pdf(SAMPLE_PDF)
        assert [m.page_no for m in manifests] == list(range(1, 11))


# ---------------------------------------------------------------------------
# 5. Synthetic scanned-page test (mock-based)
# ---------------------------------------------------------------------------

class TestSyntheticScannedPage:
    """
    The available PDFs contain only native pages.
    These tests verify the scanned branch using mock pdfplumber pages.
    The branch IS tested; it just cannot be triggered by the current fixture set.
    """

    def _make_mock_pdf(self, texts: list[str | None]):
        """Build a mock pdfplumber PDF context manager from a list of page texts."""
        pages = [_fake_page(t) for t in texts]
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = pages
        return mock_pdf

    def test_single_scanned_page(self):
        """A page returning empty text → scanned."""
        mock_pdf = self._make_mock_pdf([""])
        with patch("stages.ingest_router.pdfplumber.open", return_value=mock_pdf), \
             patch("stages.ingest_router.Path.exists", return_value=True):
            manifests = route_pdf("fake.pdf")
        assert len(manifests) == 1
        assert manifests[0].route == "scanned"

    def test_mixed_native_and_scanned(self):
        """Verify per-page routing when pages have mixed text amounts."""
        texts = [
            "A" * 2000,     # p1 → native
            "",             # p2 → scanned
            "B" * 1200,     # p3 → native
            "3",            # p4 → scanned (watermark)
            "C" * 500,      # p5 → native
        ]
        mock_pdf = self._make_mock_pdf(texts)
        with patch("stages.ingest_router.pdfplumber.open", return_value=mock_pdf), \
             patch("stages.ingest_router.Path.exists", return_value=True):
            manifests = route_pdf("fake.pdf")

        assert len(manifests) == 5
        assert manifests[0].route == "native"
        assert manifests[1].route == "scanned"
        assert manifests[2].route == "native"
        assert manifests[3].route == "scanned"
        assert manifests[4].route == "native"

        counts = count_by_route(manifests)
        assert counts["native"]  == 3
        assert counts["scanned"] == 2

    def test_page_nos_are_one_based_in_mixed(self):
        mock_pdf = self._make_mock_pdf(["A" * 100, "", "B" * 100])
        with patch("stages.ingest_router.pdfplumber.open", return_value=mock_pdf), \
             patch("stages.ingest_router.Path.exists", return_value=True):
            manifests = route_pdf("fake.pdf")
        assert [m.page_no for m in manifests] == [1, 2, 3]


# ---------------------------------------------------------------------------
# 6. PageManifest model contract — invalid route cannot be stored
# ---------------------------------------------------------------------------

class TestPageManifestContract:
    def test_pydantic_rejects_invalid_route(self):
        """
        The router uses Pydantic's PageManifest. A bug that somehow passes
        route="banana" will be caught here, not silently stored.
        """
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PageManifest(page_no=1, route="banana")

    def test_valid_manifest_construction(self):
        m = PageManifest(page_no=3, route="scanned")
        assert m.page_no == 3
        assert m.route == "scanned"


# ---------------------------------------------------------------------------
# 7. persist() — JSON round-trip
# ---------------------------------------------------------------------------

class TestPersist:
    def test_persist_creates_file(self):
        manifests = [
            PageManifest(page_no=1, route="native"),
            PageManifest(page_no=2, route="scanned"),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "sub" / "page_manifest.json"
            result_path = persist(manifests, out)
            assert result_path == out
            assert out.exists()

    def test_persist_json_structure(self):
        manifests = [
            PageManifest(page_no=1, route="native"),
            PageManifest(page_no=2, route="scanned"),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "page_manifest.json"
            persist(manifests, out)
            data = json.loads(out.read_text(encoding="utf-8"))

        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0] == {"page_no": 1, "route": "native"}
        assert data[1] == {"page_no": 2, "route": "scanned"}

    def test_persist_round_trip_to_page_manifest(self):
        """JSON persisted by persist() must deserialise back to valid PageManifest."""
        manifests = [PageManifest(page_no=i, route="native") for i in range(1, 4)]
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "page_manifest.json"
            persist(manifests, out)
            data = json.loads(out.read_text(encoding="utf-8"))
            restored = [PageManifest.model_validate(d) for d in data]

        assert restored == manifests

    def test_persist_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            deep_path = Path(tmpdir) / "a" / "b" / "c" / "manifest.json"
            persist([PageManifest(page_no=1, route="native")], deep_path)
            assert deep_path.exists()


# ---------------------------------------------------------------------------
# 8. Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_nonexistent_pdf_raises(self):
        with pytest.raises(FileNotFoundError):
            route_pdf("does_not_exist.pdf")

    def test_none_text_from_pdfplumber_does_not_crash(self):
        """pdfplumber returns None (not "") on some rasterised pages."""
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [_fake_page(None)]
        with patch("stages.ingest_router.pdfplumber.open", return_value=mock_pdf), \
             patch("stages.ingest_router.Path.exists", return_value=True):
            manifests = route_pdf("fake.pdf")
        assert manifests[0].route == "scanned"


# ---------------------------------------------------------------------------
# 9. count_by_route
# ---------------------------------------------------------------------------

class TestCountByRoute:
    def test_all_native(self):
        m = [PageManifest(page_no=i, route="native") for i in range(1, 4)]
        assert count_by_route(m) == {"native": 3, "scanned": 0}

    def test_all_scanned(self):
        m = [PageManifest(page_no=i, route="scanned") for i in range(1, 3)]
        assert count_by_route(m) == {"native": 0, "scanned": 2}

    def test_mixed(self):
        m = [
            PageManifest(page_no=1, route="native"),
            PageManifest(page_no=2, route="scanned"),
            PageManifest(page_no=3, route="native"),
        ]
        assert count_by_route(m) == {"native": 2, "scanned": 1}

    def test_empty(self):
        assert count_by_route([]) == {"native": 0, "scanned": 0}
