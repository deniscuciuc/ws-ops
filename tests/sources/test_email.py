"""Tests for EmailSource."""

from __future__ import annotations

from src.sources.email import decode_header_value, parse_email_date


class TestEmailHelpers:
    def test_decode_header_ascii(self) -> None:
        assert decode_header_value("Hello") == "Hello"

    def test_decode_header_empty(self) -> None:
        assert decode_header_value(None) == ""
        assert decode_header_value("") == ""

    def test_parse_date_valid(self) -> None:
        dt = parse_email_date("Mon, 01 Jan 2024 12:00:00 +0000")
        assert dt is not None
        assert dt.year == 2024

    def test_parse_date_empty(self) -> None:
        dt = parse_email_date(None)
        assert dt is not None

    def test_parse_date_invalid(self) -> None:
        dt = parse_email_date("garbage")
        assert dt is not None
