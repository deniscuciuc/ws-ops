"""Tests for EmailSource."""

from __future__ import annotations

from src.sources.email import _decode_header_value, _parse_date


class TestEmailHelpers:
    def test_decode_header_ascii(self) -> None:
        assert _decode_header_value("Hello") == "Hello"

    def test_decode_header_empty(self) -> None:
        assert _decode_header_value(None) == ""
        assert _decode_header_value("") == ""

    def test_parse_date_valid(self) -> None:
        dt = _parse_date("Mon, 01 Jan 2024 12:00:00 +0000")
        assert dt is not None
        assert dt.year == 2024

    def test_parse_date_empty(self) -> None:
        dt = _parse_date(None)
        assert dt is not None

    def test_parse_date_invalid(self) -> None:
        dt = _parse_date("garbage")
        assert dt is not None
