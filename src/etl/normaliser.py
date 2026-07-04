"""
normaliser.py — Data cleaning functions for Nifty 100 ETL pipeline.

Two jobs:
1. normalize_year()   — converts any date string to YYYY-MM format
2. normalize_ticker() — makes company IDs uppercase and stripped

These run on EVERY row of data before it touches the database.

Author: Pranjal
Sprint: 1 — Day 2
"""

import re
import logging

# Set up logger for this file
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# MONTH NAME → NUMBER MAP
# Used to convert "Mar" → "03", "December" → "12" etc.
# ─────────────────────────────────────────────────────────────────────────────

MONTH_MAP = {
    # Short forms
    "jan": "01",
    "feb": "02",
    "mar": "03",
    "apr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "aug": "08",
    "sep": "09",
    "oct": "10",
    "nov": "11",
    "dec": "12",
    # Full forms
    "january":   "01",
    "february":  "02",
    "march":     "03",
    "april":     "04",
    "june":      "06",
    "july":      "07",
    "august":    "08",
    "september": "09",
    "october":   "10",
    "november":  "11",
    "december":  "12",
}


# ─────────────────────────────────────────────────────────────────────────────
# REGEX PATTERNS
# Compiled once here — much faster than compiling inside function every call
# ─────────────────────────────────────────────────────────────────────────────

# Matches: 2023-03  or  2023-3
_RE_ALREADY_DONE = re.compile(r"^(\d{4})-(\d{1,2})$")

# Matches: FY23  FY2023  fy24  Fy2024
_RE_FY = re.compile(r"^[Ff][Yy](\d{2,4})$")

# Matches: Mar-23  Mar 23  March-2023  march 2023  DEC-2022  December 22
_RE_MONTH_YEAR = re.compile(r"^([A-Za-z]+)[\s\-]+(\d{2,4})$")

# Matches: 2023  2010  2024  (bare 4-digit year only)
_RE_BARE_YEAR = re.compile(r"^(\d{4})$")


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: expand 2-digit year to 4-digit
# ─────────────────────────────────────────────────────────────────────────────

def _expand_year(yr: str) -> str:
    """
    Convert 2-digit year string to 4-digit.

    Examples:
        "23" → "2023"
        "10" → "2010"
        "99" → "1999"
        "2023" → "2023"  (already 4 digits, unchanged)
    """
    if len(yr) == 4:
        return yr
    # 00-29 → 2000s,  30-99 → 1900s
    if int(yr) <= 29:
        return "20" + yr
    else:
        return "19" + yr


# ─────────────────────────────────────────────────────────────────────────────
# MAIN FUNCTION 1: normalize_year()
# ─────────────────────────────────────────────────────────────────────────────

def normalize_year(raw) -> str:
    """
    Convert any financial year string to standard YYYY-MM format.

    Handles every format found in source Excel files:

    Input           Output      Notes
    -----------     --------    ---------------------------
    "Mar-23"     →  "2023-03"   Standard format (most common)
    "Mar 23"     →  "2023-03"   Space instead of dash
    "March-2023" →  "2023-03"   Full month name
    "march 2023" →  "2023-03"   Lowercase full name
    "MAR-23"     →  "2023-03"   Uppercase
    "FY23"       →  "2023-03"   FY prefix
    "FY2023"     →  "2023-03"   FY prefix with full year
    "fy24"       →  "2024-03"   Lowercase FY
    "2023"       →  "2023-03"   Bare year (assumes March)
    "2023-03"    →  "2023-03"   Already normalised — pass through
    "2023-3"     →  "2023-03"   Single digit month — pad it
    "Dec-22"     →  "2022-12"   December year-end company
    "Dec-2022"   →  "2022-12"   December year-end full year
    "Jun-23"     →  "2023-06"   June year-end (some banks)
    "garbage"    →  "PARSE_ERROR"  Unknown format

    Args:
        raw: The raw year value from Excel (string, int, float)

    Returns:
        Normalised string in "YYYY-MM" format, or "PARSE_ERROR"
    """

    # ── Handle non-string inputs ───────────────────────────────────────────
    # Excel sometimes reads years as integers (2023) or floats (2023.0)
    if raw is None:
        return "PARSE_ERROR"

    if isinstance(raw, (int, float)):
        # Convert 2023.0 → "2023"
        raw = str(int(raw))

    # Clean up whitespace
    value = str(raw).strip()

    # Empty string check
    if not value:
        return "PARSE_ERROR"

    # ── Pattern 1: Already normalised → 2023-03 or 2023-3 ────────────────
    m = _RE_ALREADY_DONE.match(value)
    if m:
        year  = m.group(1)
        month = m.group(2).zfill(2)   # "3" → "03"
        return f"{year}-{month}"

    # ── Pattern 2: FY prefix → FY23, FY2023, fy24 ────────────────────────
    m = _RE_FY.match(value)
    if m:
        yr = _expand_year(m.group(1))
        return f"{yr}-03"              # FY always ends in March

    # ── Pattern 3: Month-Year → Mar-23, March 2023, Dec-2022 ─────────────
    m = _RE_MONTH_YEAR.match(value)
    if m:
        month_str = m.group(1).lower()
        yr_str    = m.group(2)

        # Look up month number
        month_num = MONTH_MAP.get(month_str)
        if month_num is None:
            logger.warning("Unknown month '%s' in '%s'", month_str, raw)
            return "PARSE_ERROR"

        yr = _expand_year(yr_str)
        return f"{yr}-{month_num}"

    # ── Pattern 4: Bare 4-digit year → 2023 ──────────────────────────────
    m = _RE_BARE_YEAR.match(value)
    if m:
        # Assume March year-end (standard Indian financial year)
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
    "M&M "      →  "M&M"         strips trailing space
    None        →  ""            None → empty string
    ""          →  ""            empty stays empty

    Args:
        raw: The raw ticker value from Excel

    Returns:
        Normalised uppercase ticker string, or "" if input is None/empty
    """
    if raw is None:
        return ""

    if not isinstance(raw, str):
        raw = str(raw)

    return raw.strip().upper()


# ─────────────────────────────────────────────────────────────────────────────
# SERIES VERSIONS (for applying to entire DataFrame columns at once)
# ─────────────────────────────────────────────────────────────────────────────

def normalize_year_series(series):
    """
    Apply normalize_year() to an entire pandas Series.

    Usage:
        df["year"] = normalize_year_series(df["year"])

    Args:
        series: pandas Series of raw year strings

    Returns:
        pandas Series of normalised year strings
    """
    return series.fillna("").astype(str).apply(normalize_year)


def normalize_ticker_series(series):
    """
    Apply normalize_ticker() to an entire pandas Series.

    Usage:
        df["company_id"] = normalize_ticker_series(df["company_id"])

    Args:
        series: pandas Series of raw ticker strings

    Returns:
        pandas Series of normalised uppercase tickers
    """
    return series.fillna("").astype(str).str.strip().str.upper()


# ─────────────────────────────────────────────────────────────────────────────
# QUICK TEST — run this file directly to test
# python src/etl/normaliser.py
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing normalize_year():")
    print("-" * 40)

    test_cases = [
        "Mar-23",
        "Mar 23",
        "March-2023",
        "march 2023",
        "MAR-23",
        "FY23",
        "FY2023",
        "fy24",
        "2023",
        "2023-03",
        "2023-3",
        "Dec-22",
        "Dec-2022",
        "Jun-23",
        "garbage",
        None,
        "",
    ]

    for case in test_cases:
        result = normalize_year(case)
        print(f"  normalize_year({str(case):<20}) → {result}")

    print()
    print("Testing normalize_ticker():")
    print("-" * 40)

    ticker_cases = [
        "tcs",
        "  TCS  ",
        "bajaj-auto",
        "m&m",
        "HDFCBANK",
        None,
        "",
    ]

    for case in ticker_cases:
        result = normalize_ticker(case)
        print(f"  normalize_ticker({str(case):<15}) → {result}")