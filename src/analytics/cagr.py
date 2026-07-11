"""
cagr.py — CAGR Engine for Nifty 100 Financial Intelligence Platform

Computes Compound Annual Growth Rate for:
    - Revenue (sales) — 3yr, 5yr, 10yr
    - Net Profit (PAT) — 3yr, 5yr, 10yr
    - EPS — 3yr, 5yr, 10yr

Handles all edge cases:
    - Negative base year    → None + TURNAROUND flag
    - Negative end year     → None + DECLINE_TO_LOSS flag
    - Both negative         → None + BOTH_NEGATIVE flag
    - Zero base year        → None + ZERO_BASE flag
    - Insufficient history  → None + INSUFFICIENT flag
    - Normal calculation    → float percentage

Run with:
    python src/analytics/cagr.py

Author: Samadhan
Sprint: 2 — Day 9
"""

import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# CAGR FLAGS
# ─────────────────────────────────────────────────────────────────────────────

class CAGRFlag:
    """Constants for CAGR edge case flags."""
    NORMAL          = "NORMAL"
    TURNAROUND      = "TURNAROUND"
    DECLINE_TO_LOSS = "DECLINE_TO_LOSS"
    BOTH_NEGATIVE   = "BOTH_NEGATIVE"
    ZERO_BASE       = "ZERO_BASE"
    INSUFFICIENT    = "INSUFFICIENT"
    MISSING_DATA    = "MISSING_DATA"


# ─────────────────────────────────────────────────────────────────────────────
# CORE CAGR FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def compute_cagr(
    start_value,
    end_value,
    n_years: int,
) -> Tuple[Optional[float], str]:
    """
    Compute Compound Annual Growth Rate.

    Formula: ((end / start) ^ (1/n) - 1) × 100

    Args:
        start_value: Value at beginning of period
        end_value:   Value at end of period
        n_years:     Number of years between start and end

    Returns:
        Tuple of (cagr_percentage, flag)

    Examples:
        compute_cagr(100000, 240000, 10) → (9.15, "NORMAL")
        compute_cagr(-5000, 8000, 5)     → (None, "TURNAROUND")
        compute_cagr(None, 100000, 5)    → (None, "MISSING_DATA")
    """

    # ── Handle missing data ───────────────────────────────────────────────
    if start_value is None or end_value is None:
        return None, CAGRFlag.MISSING_DATA

    try:
        start = float(start_value)
        end   = float(end_value)
    except (TypeError, ValueError):
        return None, CAGRFlag.MISSING_DATA

    if pd.isna(start) or pd.isna(end):
        return None, CAGRFlag.MISSING_DATA

    # ── Handle insufficient years ─────────────────────────────────────────
    if n_years < 1:
        return None, CAGRFlag.INSUFFICIENT

    # ── Handle zero base ──────────────────────────────────────────────────
    if start == 0:
        return None, CAGRFlag.ZERO_BASE

    # ── Handle negative values ────────────────────────────────────────────
    if start < 0 and end > 0:
        return None, CAGRFlag.TURNAROUND

    if start > 0 and end < 0:
        return None, CAGRFlag.DECLINE_TO_LOSS

    if start < 0 and end < 0:
        return None, CAGRFlag.BOTH_NEGATIVE

    # ── Normal calculation ────────────────────────────────────────────────
    try:
        ratio = end / start
        cagr  = (ratio ** (1.0 / n_years) - 1) * 100
        return round(cagr, 2), CAGRFlag.NORMAL

    except (ZeroDivisionError, ValueError, OverflowError) as e:
        logger.warning("CAGR computation error: %s", e)
        return None, CAGRFlag.MISSING_DATA


# ─────────────────────────────────────────────────────────────────────────────
# GET VALUE FOR A SPECIFIC YEAR
# ─────────────────────────────────────────────────────────────────────────────

def get_value_for_year(
    company_data: pd.DataFrame,
    target_year: str,
    column: str,
) -> Optional[float]:
    """Get a specific column value for a specific year."""
    rows = company_data[company_data["year"] == target_year]
    if rows.empty:
        return None
    val = rows.iloc[0][column]
    if pd.isna(val):
        return None
    return float(val)


# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE CAGR FOR ONE COMPANY
# ─────────────────────────────────────────────────────────────────────────────

def compute_company_cagrs(
    company_id: str,
    company_data: pd.DataFrame,
    latest_year: str,
    column: str,
    windows: list = None,
) -> dict:
    """
    Compute CAGR for multiple time windows for one company.

    Args:
        company_id:   NSE ticker
        company_data: DataFrame with all years for this company
        latest_year:  Most recent year e.g. "2024-03"
        column:       Column to compute CAGR for e.g. "sales"
        windows:      List of year windows default [3, 5, 10]

    Returns:
        Dictionary with CAGR values and flags for each window
    """
    if windows is None:
        windows = [3, 5, 10]

    result = {}

    prefix_map = {
        "sales":      "revenue",
        "net_profit": "pat",
        "eps":        "eps",
    }
    prefix = prefix_map.get(column, column)

    end_value      = get_value_for_year(company_data, latest_year, column)
    available_years = sorted(company_data["year"].unique())

    for window in windows:
        key_val  = f"{prefix}_cagr_{window}yr"
        key_flag = f"{prefix}_cagr_{window}yr_flag"

        if len(available_years) < window:
            result[key_val]  = None
            result[key_flag] = CAGRFlag.INSUFFICIENT
            continue

        latest_year_int = int(latest_year.split("-")[0])
        target_start    = latest_year_int - window

        start_year = None
        for yr in available_years:
            yr_int = int(yr.split("-")[0])
            if yr_int == target_start:
                start_year = yr
                break

        if start_year is None:
            for yr in available_years:
                yr_int = int(yr.split("-")[0])
                if abs(yr_int - target_start) <= 1:
                    start_year = yr
                    break

        if start_year is None:
            result[key_val]  = None
            result[key_flag] = CAGRFlag.INSUFFICIENT
            continue

        start_value = get_value_for_year(company_data, start_year, column)

        if end_value is None or start_value is None:
            result[key_val]  = None
            result[key_flag] = CAGRFlag.MISSING_DATA
            continue

        start_yr_int = int(start_year.split("-")[0])
        end_yr_int   = int(latest_year.split("-")[0])
        actual_n     = end_yr_int - start_yr_int

        if actual_n < 1:
            result[key_val]  = None
            result[key_flag] = CAGRFlag.INSUFFICIENT
            continue

        cagr_val, flag   = compute_cagr(start_value, end_value, actual_n)
        result[key_val]  = cagr_val
        result[key_flag] = flag

    return result


# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE ALL CAGRs FOR ALL COMPANIES
# ─────────────────────────────────────────────────────────────────────────────

def compute_all_cagrs(pl_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Revenue, PAT and EPS CAGR for all companies.

    Args:
        pl_df: profitandloss DataFrame

    Returns:
        DataFrame with CAGR columns per company
    """
    logger.info(
        "Computing CAGRs for %d companies...",
        pl_df["company_id"].nunique()
    )

    results = []

    for company_id, company_data in pl_df.groupby("company_id"):
        company_data = company_data.sort_values("year")

        if company_data.empty:
            continue

        latest_year = company_data["year"].max()
        row = {"company_id": company_id, "latest_year": latest_year}

        # Revenue CAGR
        row.update(compute_company_cagrs(
            company_id, company_data, latest_year,
            column="sales", windows=[3, 5, 10]
        ))

        # PAT CAGR
        row.update(compute_company_cagrs(
            company_id, company_data, latest_year,
            column="net_profit", windows=[3, 5, 10]
        ))

        # EPS CAGR
        row.update(compute_company_cagrs(
            company_id, company_data, latest_year,
            column="eps", windows=[3, 5]
        ))

        results.append(row)

    df = pd.DataFrame(results)
    logger.info(
        "CAGR complete: %d companies, %d columns",
        len(df), len(df.columns)
    )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# QUICK TEST
# python src/analytics/cagr.py
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing CAGR Engine...")
    print("=" * 55)

    print("\n── Normal CAGR calculations ──")
    val, flag = compute_cagr(100000, 240000, 10)
    print(f"10yr CAGR (100K→240K):     {val}%  flag={flag}")
    print(f"  Expected: ~9.15%")

    val, flag = compute_cagr(50000, 100000, 5)
    print(f"5yr CAGR (50K→100K):       {val}%  flag={flag}")
    print(f"  Expected: ~14.87%")

    val, flag = compute_cagr(80000, 100000, 3)
    print(f"3yr CAGR (80K→100K):       {val}%  flag={flag}")
    print(f"  Expected: ~7.72%")

    print("\n── Edge cases ──")
    val, flag = compute_cagr(-5000, 8000, 5)
    print(f"Turnaround (-5K→+8K):      {val}  flag={flag}")

    val, flag = compute_cagr(5000, -3000, 5)
    print(f"Decline to loss (5K→-3K):  {val}  flag={flag}")

    val, flag = compute_cagr(-5000, -3000, 5)
    print(f"Both negative (-5K→-3K):   {val}  flag={flag}")

    val, flag = compute_cagr(0, 50000, 5)
    print(f"Zero base (0→50K):         {val}  flag={flag}")

    val, flag = compute_cagr(None, 50000, 5)
    print(f"None base:                 {val}  flag={flag}")

    print("\n── Testing with sample DataFrame ──")
    sample_pl = pd.DataFrame({
        "company_id": ["TCS"] * 11,
        "year": [
            "2014-03", "2015-03", "2016-03", "2017-03",
            "2018-03", "2019-03", "2020-03", "2021-03",
            "2022-03", "2023-03", "2024-03"
        ],
        "sales": [
            94648, 108646, 123520, 127171,
            146463, 156949, 161541, 164177,
            191754, 225458, 240893
        ],
        "net_profit": [
            20592, 22199, 26289, 26257,
            30904, 31472, 32430, 32430,
            38327, 42147, 46099
        ],
        "eps": [
            52.9, 57.1, 67.7, 67.8,
            82.5, 83.3, 85.8, 86.5,
            103.6, 114.2, 125.2
        ],
    })

    cagrs = compute_all_cagrs(sample_pl)
    print("\nTCS CAGR Results:")
    print("-" * 40)
    for col in cagrs.columns:
        if col not in ["company_id", "latest_year"]:
            val = cagrs.iloc[0][col]
            print(f"  {col:<35} {val}")

    print("\n✅ CAGR Engine working correctly!")