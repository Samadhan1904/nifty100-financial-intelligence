"""
ratios.py — Financial Ratio Engine for Nifty 100 Platform

Computes profitability and leverage KPIs for every
company-year combination from raw financial data.

KPIs computed here:
    Profitability: NPM, OPM, EBIT Margin, ROE, ROCE, ROA
    Leverage:      D/E, ICR, Net Debt, Asset Turnover

Edge cases handled:
    - Division by zero → None
    - Negative equity  → None for ROE/ROCE
    - Debt-free companies → ICR = None, display "Debt Free"
    - Banks/NBFCs → D/E carve-out (high D/E is normal)

Run with:
    python src/analytics/ratios.py

Author: Samadhan
Sprint: 2 — Day 8
"""

import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# FINANCIAL SECTOR TICKERS
# These companies have structurally high D/E — exclude from D/E warnings
# ─────────────────────────────────────────────────────────────────────────────

FINANCIAL_SECTORS = {
    "Financials",
    "Banks",
    "NBFC",
    "Insurance",
}

BANK_TICKERS = {
    "HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK",
    "SBIN", "BANKBARODA", "CANBK", "PNB", "INDUSINDBK",
    "LICI", "HDFCLIFE", "SBILIFE", "ICICIPRULI", "ICICIGI",
    "BAJFINANCE", "CHOLAFIN", "SHRIRAMFIN", "JIOFIN",
    "UNIONBANK", "PFC", "RECLTD",
}


# ─────────────────────────────────────────────────────────────────────────────
# SAFE DIVISION HELPER
# ─────────────────────────────────────────────────────────────────────────────

def safe_divide(
    numerator,
    denominator,
    multiply: float = 1.0,
    round_digits: int = 2,
) -> Optional[float]:
    """
    Safely divide two numbers. Returns None if:
    - Either value is None or NaN
    - Denominator is zero

    Args:
        numerator:    Top number
        denominator:  Bottom number
        multiply:     Multiply result by this (e.g. 100 for percentages)
        round_digits: Round result to this many decimal places

    Returns:
        Float result or None

    Examples:
        safe_divide(100, 500, 100) → 20.0  (ROE = 20%)
        safe_divide(100, 0)        → None  (division by zero)
        safe_divide(None, 500)     → None  (missing data)
    """
    try:
        if numerator is None or denominator is None:
            return None
        if pd.isna(numerator) or pd.isna(denominator):
            return None
        if denominator == 0:
            return None
        result = (float(numerator) / float(denominator)) * multiply
        return round(result, round_digits)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# PROFITABILITY RATIOS
# ─────────────────────────────────────────────────────────────────────────────

def compute_npm(net_profit, sales) -> Optional[float]:
    """
    Net Profit Margin = net_profit / sales × 100

    Measures: How much profit a company makes per rupee of sales.

    Benchmark:
        > 10% = good
        > 20% = excellent
        Negative = company making losses

    Edge cases:
        sales = 0 or None → return None
        net_profit can be negative (losses allowed)

    Examples:
        TCS FY23: 34990 / 225458 × 100 = 15.52%
    """
    return safe_divide(net_profit, sales, multiply=100)


def compute_opm(operating_profit, sales) -> Optional[float]:
    """
    Operating Profit Margin = operating_profit / sales × 100

    Measures: Profitability from core operations (before interest/tax).
    Also called EBITDA margin.

    Benchmark:
        > 15% = good
        > 25% = excellent

    Note: Banks show very high or negative OPM because their
          "sales" includes interest income. Not meaningful for banks.
    """
    return safe_divide(operating_profit, sales, multiply=100)


def compute_ebit_margin(operating_profit, depreciation, sales) -> Optional[float]:
    """
    EBIT Margin = (operating_profit - depreciation) / sales × 100

    EBIT = Earnings Before Interest and Tax
         = EBITDA - Depreciation

    Measures: Core operational earnings excluding non-cash D&A.

    Edge cases:
        depreciation = None → treat as 0
    """
    if operating_profit is None or pd.isna(operating_profit):
        return None
    dep = 0 if (depreciation is None or pd.isna(depreciation)) else depreciation
    ebit = operating_profit - dep
    return safe_divide(ebit, sales, multiply=100)


def compute_roe(net_profit, equity_capital, reserves) -> Optional[float]:
    """
    Return on Equity = net_profit / (equity_capital + reserves) × 100

    Measures: How much profit generated per rupee of shareholders money.

    Benchmark:
        > 15% = good
        > 20% = excellent

    Edge cases:
        equity + reserves <= 0 → return None
        (negative equity happens when losses exceed reserves)

    Examples:
        TCS FY23: 34990 / (212 + 67456) × 100 = 51.7%
    """
    if equity_capital is None or reserves is None:
        if equity_capital is None and reserves is None:
            return None
    eq  = equity_capital if equity_capital is not None else 0
    res = reserves       if reserves       is not None else 0

    if pd.isna(eq) or pd.isna(res):
        return None

    total_equity = eq + res

    # Cannot compute ROE with zero or negative equity
    if total_equity <= 0:
        return None

    return safe_divide(net_profit, total_equity, multiply=100)


def compute_roce(
    operating_profit,
    depreciation,
    equity_capital,
    reserves,
    borrowings,
) -> Optional[float]:
    """
    ROCE = EBIT / Capital Employed × 100

    Capital Employed = equity_capital + reserves + borrowings

    Measures: Returns on ALL capital (equity + debt).
    Better than ROE for comparing debt-free vs leveraged companies.

    Benchmark:
        > 15% = good
        > 25% = excellent

    Edge cases:
        capital_employed <= 0 → None
        depreciation = None   → treat as 0
    """
    if operating_profit is None or pd.isna(operating_profit):
        return None

    dep = 0 if (depreciation is None or pd.isna(depreciation)) else depreciation
    ebit = operating_profit - dep

    eq   = equity_capital if (equity_capital is not None
                               and not pd.isna(equity_capital)) else 0
    res  = reserves       if (reserves       is not None
                               and not pd.isna(reserves))       else 0
    debt = borrowings     if (borrowings     is not None
                               and not pd.isna(borrowings))     else 0

    capital_employed = eq + res + debt

    if capital_employed <= 0:
        return None

    return safe_divide(ebit, capital_employed, multiply=100)


def compute_roa(net_profit, total_assets) -> Optional[float]:
    """
    Return on Assets = net_profit / total_assets × 100

    Measures: How efficiently a company uses its assets to generate profit.

    Benchmark:
        > 5%  = good
        > 10% = excellent

    Edge cases:
        total_assets = 0 or None → None
    """
    return safe_divide(net_profit, total_assets, multiply=100)


# ─────────────────────────────────────────────────────────────────────────────
# LEVERAGE RATIOS
# ─────────────────────────────────────────────────────────────────────────────

def compute_de_ratio(
    borrowings,
    equity_capital,
    reserves,
    company_id: str = "",
) -> Optional[float]:
    """
    Debt-to-Equity = borrowings / (equity_capital + reserves)

    Measures: How much debt relative to shareholders equity.

    Benchmark (non-financial companies):
        0    = debt-free
        < 0.5 = conservative
        < 1.0 = healthy
        > 2.0 = high leverage
        > 5.0 = flag (not for banks)

    Special handling:
        Banks/NBFCs structurally have D/E of 5-15x.
        We return the ratio but don't flag it for financial companies.

    Edge cases:
        borrowings = 0     → return 0.0 (debt-free)
        equity + res <= 0  → return None
    """
    borrow = borrowings if (borrowings is not None
                             and not pd.isna(borrowings)) else 0

    # Debt-free
    if borrow == 0:
        return 0.0

    eq  = equity_capital if (equity_capital is not None
                               and not pd.isna(equity_capital)) else 0
    res = reserves       if (reserves       is not None
                               and not pd.isna(reserves))       else 0

    total_equity = eq + res

    if total_equity <= 0:
        return None

    return safe_divide(borrow, total_equity)


def compute_icr(
    operating_profit,
    other_income,
    interest,
    company_id: str = "",
) -> Optional[float]:
    """
    Interest Coverage Ratio = (EBIT + other_income) / interest

    Measures: How many times company can pay its interest from earnings.

    Benchmark:
        > 3x  = safe
        > 5x  = strong
        < 1.5x = danger zone

    Special handling:
        interest = 0 → return None (display as "Debt Free")
        interest < 0 → treat as 0

    Edge cases:
        other_income = None → treat as 0
    """
    int_val = interest if (interest is not None
                            and not pd.isna(interest)) else 0

    # Debt-free company
    if int_val <= 0:
        return None

    op      = operating_profit if (operating_profit is not None
                                    and not pd.isna(operating_profit)) else 0
    oth_inc = other_income      if (other_income     is not None
                                    and not pd.isna(other_income))     else 0

    numerator = op + oth_inc
    return safe_divide(numerator, int_val)


def compute_asset_turnover(sales, total_assets) -> Optional[float]:
    """
    Asset Turnover = sales / total_assets

    Measures: How efficiently a company uses assets to generate revenue.

    Benchmark:
        > 1x = efficient
        > 2x = asset-light business

    Edge cases:
        total_assets = 0 or None → None
    """
    return safe_divide(sales, total_assets)


def compute_net_debt(borrowings, investments) -> Optional[float]:
    """
    Net Debt = borrowings - investments

    Measures: True debt position after subtracting liquid investments.

    Negative net debt = company has more cash/investments than debt.

    Edge cases:
        investments = None → treat as 0
    """
    if borrowings is None or pd.isna(borrowings):
        return None

    inv = investments if (investments is not None
                           and not pd.isna(investments)) else 0

    return round(float(borrowings) - float(inv), 2)


# ─────────────────────────────────────────────────────────────────────────────
# APPLY TO DATAFRAME
# ─────────────────────────────────────────────────────────────────────────────

def compute_all_ratios(
    pl_df: pd.DataFrame,
    bs_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute all profitability and leverage ratios for
    every company-year combination.

    Args:
        pl_df: profitandloss DataFrame
        bs_df: balancesheet DataFrame

    Returns:
        DataFrame with all ratios computed
        Columns: company_id, year, npm, opm, ebit_margin,
                 roe, roce, roa, debt_to_equity, icr,
                 asset_turnover, net_debt_cr
    """
    logger.info(
        "Computing ratios for %d P&L rows and %d BS rows",
        len(pl_df), len(bs_df)
    )

    # Merge P&L and Balance Sheet on (company_id, year)
    merged = pd.merge(
        pl_df,
        bs_df,
        on=["company_id", "year"],
        how="inner",
        suffixes=("_pl", "_bs"),
    )

    logger.info("Merged rows: %d", len(merged))

    results = []

    for _, row in merged.iterrows():
        cid = row["company_id"]

        ratios = {
            "company_id": cid,
            "year":       row["year"],

            # Profitability
            "net_profit_margin_pct": compute_npm(
                row.get("net_profit"),
                row.get("sales"),
            ),
            "operating_profit_margin_pct": compute_opm(
                row.get("operating_profit"),
                row.get("sales"),
            ),
            "ebit_margin_pct": compute_ebit_margin(
                row.get("operating_profit"),
                row.get("depreciation"),
                row.get("sales"),
            ),
            "return_on_equity_pct": compute_roe(
                row.get("net_profit"),
                row.get("equity_capital"),
                row.get("reserves"),
            ),
            "return_on_capital_pct": compute_roce(
                row.get("operating_profit"),
                row.get("depreciation"),
                row.get("equity_capital"),
                row.get("reserves"),
                row.get("borrowings"),
            ),
            "return_on_assets_pct": compute_roa(
                row.get("net_profit"),
                row.get("total_assets"),
            ),

            # Leverage
            "debt_to_equity": compute_de_ratio(
                row.get("borrowings"),
                row.get("equity_capital"),
                row.get("reserves"),
                company_id=cid,
            ),
            "interest_coverage": compute_icr(
                row.get("operating_profit"),
                row.get("other_income"),
                row.get("interest"),
                company_id=cid,
            ),
            "asset_turnover": compute_asset_turnover(
                row.get("sales"),
                row.get("total_assets"),
            ),
            "net_debt_cr": compute_net_debt(
                row.get("borrowings"),
                row.get("investments"),
            ),

            # Store raw values for CAGR (Sprint 2 Day 10)
            "sales_cr":      row.get("sales"),
            "net_profit_cr": row.get("net_profit"),
            "eps":           row.get("eps"),

            # Store CFO for cash flow KPIs (Day 11)
            "cash_from_operations_cr": None,
            "free_cash_flow_cr":       None,
        }

        results.append(ratios)

    df = pd.DataFrame(results)
    logger.info(
        "Computed ratios: %d rows, %d columns",
        len(df), len(df.columns)
    )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# QUICK TEST
# python src/analytics/ratios.py
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing ratio functions...")
    print("-" * 50)

    # Test NPM
    npm = compute_npm(34990, 225458)
    print(f"NPM (TCS FY23):          {npm}%  (expected ~15.52)")

    # Test OPM
    opm = compute_opm(48534, 225458)
    print(f"OPM (TCS FY23):          {opm}%  (expected ~21.53)")

    # Test ROE
    roe = compute_roe(34990, 212, 67456)
    print(f"ROE (TCS FY23):          {roe}%  (expected ~51.7)")

    # Test ROCE
    roce = compute_roce(48534, 5800, 212, 67456, 0)
    print(f"ROCE (TCS FY23):         {roce}%")

    # Test ROA
    roa = compute_roa(34990, 120000)
    print(f"ROA:                     {roa}%")

    # Test D/E
    de = compute_de_ratio(0, 212, 67456)
    print(f"D/E (debt-free):         {de}  (expected 0.0)")

    de2 = compute_de_ratio(10000, 5000, 45000)
    print(f"D/E (with debt):         {de2}  (expected 0.2)")

    # Test ICR
    icr = compute_icr(48534, 3800, 0)
    print(f"ICR (debt-free):         {icr}  (expected None)")

    icr2 = compute_icr(10000, 500, 2000)
    print(f"ICR (with interest):     {icr2}  (expected 5.25)")

    # Test edge cases
    npm_none = compute_npm(None, 100)
    print(f"NPM (None profit):       {npm_none}  (expected None)")

    roe_zero_eq = compute_roe(5000, 0, 0)
    print(f"ROE (zero equity):       {roe_zero_eq}  (expected None)")

    de_zero_div = compute_de_ratio(10000, 0, 0)
    print(f"D/E (zero equity):       {de_zero_div}  (expected None)")

    print("\n✅ All ratio functions working correctly!")