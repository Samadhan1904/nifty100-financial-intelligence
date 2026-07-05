"""
normaliser.py — Data cleaning functions for Nifty 100 ETL pipeline.

Two jobs:
1. normalize_year()   — converts any date string to YYYY-MM format
2. normalize_ticker() — makes company IDs uppercase and stripped

These run on EVERY row of data before it touches the database.

Author: Samadhan
Sprint: 1 — Day 2
"""

import re
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# MONTH NAME → NUMBER MAP
# ─────────────────────────────────────────────────────────────────────────────

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    "january": "01", "february": "02", "march": "03",
    "april": "04", "june": "06", "july": "07",
    "august": "08", "september": "09", "october": "10",
    "november": "11", "december": "12",
}

# ─────────────────────────────────────────────────────────────────────────────
# REGEX PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

_RE_ALREADY_DONE = re.compile(r"^(\d{4})-(\d{1,2})$")
_RE_FY           = re.compile(r"^[Ff][Yy](\d{2,4})$")
_RE_MONTH_YEAR   = re.compile(r"^([A-Za-z]+)[\s\-]+(\d{2,4})$")
_RE_BARE_YEAR    = re.compile(r"^(\d{4})$")
_RE_PARTIAL      = re.compile(r"^([A-Za-z]+[\s\-]\d{2,4})")


# ─────────────────────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _expand_year(yr: str) -> str:
    """Convert 2-digit year to 4-digit."""
    if len(yr) == 4:
        return yr
    return "20" + yr if int(yr) <= 29 else "19" + yr


# ─────────────────────────────────────────────────────────────────────────────
# MAIN FUNCTION 1: normalize_year()
# ─────────────────────────────────────────────────────────────────────────────

def normalize_year(raw) -> str:
    """
    Convert any financial year string to standard YYYY-MM format.

    Input           Output        Notes
    -----------     --------      ---------------------------
    "Mar-23"     →  "2023-03"     Standard format (most common)
    "Mar 23"     →  "2023-03"     Space instead of dash
    "March-2023" →  "2023-03"     Full month name
    "march 2023" →  "2023-03"     Lowercase full name
    "MAR-23"     →  "2023-03"     Uppercase
    "FY23"       →  "2023-03"     FY prefix
    "FY2023"     →  "2023-03"     FY prefix with full year
    "fy24"       →  "2024-03"     Lowercase FY
    "2023"       →  "2023-03"     Bare year (assumes March)
    "2023-03"    →  "2023-03"     Already normalised
    "2023-3"     →  "2023-03"     Single digit month padded
    "Dec-22"     →  "2022-12"     December year-end company
    "Jun-23"     →  "2023-06"     June year-end banks
    "TTM"        →  "PARSE_ERROR" Trailing twelve months — skip
    "Mar 2016 9m"→  "2016-03"     Partial year — strip suffix
    "garbage"    →  "PARSE_ERROR" Unknown format
    """

    # ── Handle None ───────────────────────────────────────────────────────
    if raw is None:
        return "PARSE_ERROR"

    # ── Handle int/float (Excel sometimes gives 2023 or 2023.0) ──────────
    if isinstance(raw, (int, float)):
        raw = str(int(raw))

    # ── Clean whitespace ──────────────────────────────────────────────────
    value = str(raw).strip()

    # ── Empty string ──────────────────────────────────────────────────────
    if not value:
        return "PARSE_ERROR"

    # ── TTM = Trailing Twelve Months — not a real FY, skip it ────────────
    if value.upper() == "TTM":
        return "PARSE_ERROR"

    # ── Partial year like "Mar 2016 9m" — strip the suffix ───────────────
    partial = _RE_PARTIAL.match(value)
    if partial and value != partial.group(1).strip():
        value = partial.group(1).strip()

    # ── Pattern 1: Already normalised → 2023-03 or 2023-3 ────────────────
    m = _RE_ALREADY_DONE.match(value)
    if m:
        year  = m.group(1)
        month = m.group(2).zfill(2)
        return f"{year}-{month}"

    # ── Pattern 2: FY prefix → FY23, FY2023, fy24 ────────────────────────
    m = _RE_FY.match(value)
    if m:
        yr = _expand_year(m.group(1))
        return f"{yr}-03"

    # ── Pattern 3: Month-Year → Mar-23, March 2023, Dec-2022 ─────────────
    m = _RE_MONTH_YEAR.match(value)
    if m:
        month_str = m.group(1).lower()
        yr_str    = m.group(2)

        month_num = MONTH_MAP.get(month_str)
        if month_num is None:
            logger.warning("Unknown month '%s' in '%s'", month_str, raw)
            return "PARSE_ERROR"

        yr = _expand_year(yr_str)
        return f"{yr}-{month_num}"

    # ── Pattern 4: Bare 4-digit year → 2023 ──────────────────────────────
    m = _RE_BARE_YEAR.match(value)
    if m:
        return f"{m.group(1)}-03"

    # ── No pattern matched ────────────────────────────────────────────────
    logger.warning("Could not parse year string: '%s'", raw)
    return "PARSE_ERROR"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN FUNCTION 2: normalize_ticker()
# ─────────────────────────────────────────────────────────────────────────────

def normalize_ticker(raw) -> str:
    """
    Normalise a company NSE ticker to uppercase stripped format.

    Input          Output        Notes
    ----------     ----------    ---------------------------
    "tcs"       →  "TCS"         lowercase → uppercase
    "  TCS  "   →  "TCS"         strips whitespace
    "bajaj-auto"→  "BAJAJ-AUTO"  hyphen preserved
    "m&m"       →  "M&M"         ampersand preserved
    None        →  ""            None → empty string
    ""          →  ""            empty stays empty
    """
    if raw is None:
        return ""

    if not isinstance(raw, str):
        raw = str(raw)

    return raw.strip().upper()


# ─────────────────────────────────────────────────────────────────────────────
# SERIES VERSIONS
# ─────────────────────────────────────────────────────────────────────────────

def normalize_year_series(series):
    """Apply normalize_year() to an entire pandas Series."""
    return series.fillna("").astype(str).apply(normalize_year)


def normalize_ticker_series(series):
    """Apply normalize_ticker() to an entire pandas Series."""
    return series.fillna("").astype(str).str.strip().str.upper()


# ─────────────────────────────────────────────────────────────────────────────
# QUICK TEST
# python src/etl/normaliser.py
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing normalize_year():")
    print("-" * 40)

    test_cases = [
        "Mar-23", "Mar 23", "March-2023", "march 2023",
        "MAR-23", "FY23", "FY2023", "fy24",
        "2023", "2023-03", "2023-3",
        "Dec-22", "Dec-2022", "Jun-23",
        "TTM", "Mar 2016 9m", "2024.5",
        "garbage", None, "",
    ]

    for case in test_cases:
        result = normalize_year(case)
        print(f"  normalize_year({str(case):<22}) → {result}")

    print()
    print("Testing normalize_ticker():")
    print("-" * 40)

    ticker_cases = [
        "tcs", "  TCS  ", "bajaj-auto",
        "m&m", "HDFCBANK", None, "",
    ]

    for case in ticker_cases:
        result = normalize_ticker(case)
        print(f"  normalize_ticker({str(case):<15}) → {result}")