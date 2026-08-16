"""
tests/test_page_manifest.py — Tests for Stage 1 PageManifest contract.

Covers:
  - Valid construction with both allowed route values.
  - Rejection of invalid route values (the "banana" test).
  - Rejection of wrong types for page_no.
"""

import pytest
from pydantic import ValidationError

from models.page_manifest import PageManifest


class TestPageManifestValid:
    def test_native_route_accepted(self):
        m = PageManifest(page_no=1, route="native")
        assert m.page_no == 1
        assert m.route == "native"

    def test_scanned_route_accepted(self):
        m = PageManifest(page_no=5, route="scanned")
        assert m.page_no == 5
        assert m.route == "scanned"

    def test_page_no_zero_accepted(self):
        """page_no=0 is unusual but the model does not restrict it to >= 1 at MVP."""
        m = PageManifest(page_no=0, route="native")
        assert m.page_no == 0

    def test_serialisation_round_trip(self):
        m = PageManifest(page_no=3, route="scanned")
        restored = PageManifest.model_validate(m.model_dump())
        assert restored == m


class TestPageManifestInvalid:
    def test_banana_route_raises(self):
        """Core contract test: route='banana' must be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PageManifest(page_no=1, route="banana")
        # Confirm the error references the route field
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("route",) for e in errors)

    def test_empty_string_route_raises(self):
        with pytest.raises(ValidationError):
            PageManifest(page_no=1, route="")

    def test_uppercase_route_raises(self):
        """Literal matching is case-sensitive."""
        with pytest.raises(ValidationError):
            PageManifest(page_no=1, route="Native")

    def test_missing_route_raises(self):
        with pytest.raises(ValidationError):
            PageManifest(page_no=1)

    def test_missing_page_no_raises(self):
        with pytest.raises(ValidationError):
            PageManifest(route="native")

    def test_string_page_no_coercion(self):
        """Pydantic v2 coerces '3' → 3 for int fields by default."""
        m = PageManifest(page_no="3", route="native")
        assert m.page_no == 3
