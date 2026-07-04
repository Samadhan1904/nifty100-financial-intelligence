"""
Unit tests for normalize_year() and normalize_ticker().

35+ tests covering every possible input format.

Run with:
    pytest tests/etl/test_normalise.py -v

All tests must pass before Day 2 is complete.

Author: Samadhan
Sprint: 1 — Day 2
"""

import pytest
from src.etl.normaliser import normalize_year, normalize_ticker


# =============================================================================
# normalize_year TESTS — 25 test cases
# =============================================================================

class TestNormalizeYear:
    """Tests for the normalize_year() function."""

    # ── Standard Mar-YY format (most common in your Excel files) ──────────

    def test_mar_23_with_dash(self):
        """Mar-23 is the most common format in profitandloss.xlsx"""
        assert normalize_year("Mar-23") == "2023-03"

    def test_mar_23_with_space(self):
        """Space instead of dash should also work"""
        assert normalize_year("Mar 23") == "2023-03"

    def test_mar_lowercase(self):
        """Lowercase should work"""
        assert normalize_year("mar-23") == "2023-03"

    def test_mar_uppercase(self):
        """Uppercase should work"""
        assert normalize_year("MAR-23") == "2023-03"

    def test_march_full_name_with_dash(self):
        """Full month name with dash"""
        assert normalize_year("March-2023") == "2023-03"

    def test_march_full_name_with_space(self):
        """Full month name with space"""
        assert normalize_year("March 2023") == "2023-03"

    def test_march_lowercase_full(self):
        """Lowercase full month name"""
        assert normalize_year("march 2023") == "2023-03"

    # ── December year-end companies (e.g. NESTLEIND) ──────────────────────

    def test_dec_22_short_year(self):
        """December year-end with 2-digit year"""
        assert normalize_year("Dec-22") == "2022-12"

    def test_dec_2022_full_year(self):
        """December year-end with 4-digit year"""
        assert normalize_year("Dec-2022") == "2022-12"

    def test_december_full_name(self):
        """Full December name"""
        assert normalize_year("December 2022") == "2022-12"

    def test_dec_lowercase(self):
        """Lowercase december"""
        assert normalize_year("dec-22") == "2022-12"

    # ── June year-end (some banks) ─────────────────────────────────────────

    def test_jun_23(self):
        """June year-end banks"""
        assert normalize_year("Jun-23") == "2023-06"

    def test_june_full_name(self):
        """Full June name"""
        assert normalize_year("June-2023") == "2023-06"

    # ── FY prefix formats ──────────────────────────────────────────────────

    def test_fy23_short(self):
        """FY with 2-digit year"""
        assert normalize_year("FY23") == "2023-03"

    def test_fy2023_long(self):
        """FY with 4-digit year"""
        assert normalize_year("FY2023") == "2023-03"

    def test_fy24(self):
        """FY24 format"""
        assert normalize_year("FY24") == "2024-03"

    def test_fy_lowercase(self):
        """Lowercase fy"""
        assert normalize_year("fy23") == "2023-03"

    def test_fy10(self):
        """Earliest year in dataset"""
        assert normalize_year("FY10") == "2010-03"

    # ── Already normalised ─────────────────────────────────────────────────

    def test_already_normalised(self):
        """2023-03 should pass through unchanged"""
        assert normalize_year("2023-03") == "2023-03"

    def test_already_normalised_single_digit_month(self):
        """2023-3 should be padded to 2023-03"""
        assert normalize_year("2023-3") == "2023-03"

    # ── Bare year ──────────────────────────────────────────────────────────

    def test_bare_year_2023(self):
        """Bare 4-digit year assumes March"""
        assert normalize_year("2023") == "2023-03"

    def test_bare_year_2010(self):
        """Earliest year in dataset"""
        assert normalize_year("2010") == "2010-03"

    def test_bare_year_2024(self):
        """Latest year in dataset"""
        assert normalize_year("2024") == "2024-03"

    # ── Integer and float inputs ───────────────────────────────────────────

    def test_integer_year(self):
        """Excel sometimes gives year as integer"""
        assert normalize_year(2023) == "2023-03"

    def test_float_year(self):
        """Excel sometimes gives year as float"""
        assert normalize_year(2023.0) == "2023-03"

    # ── Error cases ────────────────────────────────────────────────────────

    def test_garbage_string(self):
        """Unrecognised format returns PARSE_ERROR"""
        assert normalize_year("garbage") == "PARSE_ERROR"

    def test_none_input(self):
        """None input returns PARSE_ERROR"""
        assert normalize_year(None) == "PARSE_ERROR"

    def test_empty_string(self):
        """Empty string returns PARSE_ERROR"""
        assert normalize_year("") == "PARSE_ERROR"

    def test_random_text(self):
        """Random text returns PARSE_ERROR"""
        assert normalize_year("hello world") == "PARSE_ERROR"

    def test_partial_date(self):
        """Partial date returns PARSE_ERROR"""
        assert normalize_year("Mar") == "PARSE_ERROR"


# =============================================================================
# normalize_ticker TESTS — 15 test cases
# =============================================================================

class TestNormalizeTicker:
    """Tests for the normalize_ticker() function."""

    # ── Uppercase conversion ───────────────────────────────────────────────

    def test_lowercase_to_uppercase(self):
        """tcs should become TCS"""
        assert normalize_ticker("tcs") == "TCS"

    def test_mixed_case(self):
        """Mixed case should become uppercase"""
        assert normalize_ticker("HdfcBank") == "HDFCBANK"

    def test_already_uppercase(self):
        """Already uppercase should stay the same"""
        assert normalize_ticker("TCS") == "TCS"

    # ── Whitespace stripping ───────────────────────────────────────────────

    def test_leading_space(self):
        """Leading space should be stripped"""
        assert normalize_ticker("  TCS") == "TCS"

    def test_trailing_space(self):
        """Trailing space should be stripped"""
        assert normalize_ticker("TCS  ") == "TCS"

    def test_both_sides_space(self):
        """Spaces on both sides should be stripped"""
        assert normalize_ticker("  TCS  ") == "TCS"

    # ── Special characters preserved ──────────────────────────────────────

    def test_hyphen_preserved(self):
        """Hyphen in ticker should be preserved"""
        assert normalize_ticker("bajaj-auto") == "BAJAJ-AUTO"

    def test_ampersand_preserved(self):
        """Ampersand in ticker should be preserved"""
        assert normalize_ticker("m&m") == "M&M"

    def test_hyphen_uppercase(self):
        """Hyphen with uppercase"""
        assert normalize_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO"

    # ── Real company tickers ───────────────────────────────────────────────

    def test_hdfcbank(self):
        assert normalize_ticker("hdfcbank") == "HDFCBANK"

    def test_icicibank(self):
        assert normalize_ticker("icicibank") == "ICICIBANK"

    def test_reliance(self):
        assert normalize_ticker("reliance") == "RELIANCE"

    # ── Edge cases ─────────────────────────────────────────────────────────

    def test_none_returns_empty(self):
        """None input should return empty string"""
        assert normalize_ticker(None) == ""

    def test_empty_string(self):
        """Empty string should return empty string"""
        assert normalize_ticker("") == ""

    def test_integer_input(self):
        """Integer input should be handled"""
        result = normalize_ticker(123)
        assert isinstance(result, str)