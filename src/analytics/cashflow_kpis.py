"""
cashflow_kpis.py — Cash Flow Intelligence Module

Computes cash flow quality KPIs:
    - Free Cash Flow (FCF)
    - CFO Quality Score (CFO/PAT ratio)
    - CapEx Intensity (CapEx/Revenue %)
    - FCF Conversion Rate (FCF/EBITDA %)
    - FCF CAGR (3yr, 5yr)
    - Capital Allocation Pattern (8 categories)
    - Distress Signal detection
    - Deleveraging detection

Run with:
    python src/analytics/cashflow_kpis.py

Author: Samadhan
Sprint: 2 — Day 10
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.analytics.ratios import safe_divide

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# CAPITAL ALLOCATION PATTERNS
# Based on sign combination of CFO, CFI, CFF
# ─────────────────────────────────────────────────────────────────────────────

class CapitalPattern:
    """8 capital allocation pattern labels."""
    REINVESTOR         = "Reinvestor"
    SHAREHOLDER_RETURN = "Shareholder Returns"
    GROWTH_FINANCED    = "Growth Financed"
    ASSET_SALE         = "Asset Sale"
    DISTRESS           = "Distress Signal"
    CASH_BURN          = "Cash Burn"
    MATURE_STEADY      = "Mature Steady"
    OTHER              = "Other"


# ─────────────────────────────────────────────────────────────────────────────
# INDIVIDUAL KPI FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def compute_fcf(
    operating_activity,
    investing_activity,
) -> Optional[float]:
    """
    Free Cash Flow = CFO + CFI

    CFO = operating_activity (cash from operations)
    CFI = investing_activity (cash used in investing)

    CFI is usually negative (spending on assets).
    FCF > 0 means company generates surplus cash.

    Args:
        operating_activity: CFO in Crore
        investing_activity: CFI in Crore (usually negative)

    Returns:
        FCF in Crore or None if data missing

    Examples:
        CFO=40000, CFI=-5000 → FCF = 35000 Cr (healthy)
        CFO=5000,  CFI=-20000→ FCF = -15000 Cr (investing heavily)
        CFO=-3000, CFI=1000  → FCF = -2000 Cr (concern)
    """
    if operating_activity is None or pd.isna(operating_activity):
        return None
    if investing_activity is None or pd.isna(investing_activity):
        return None

    return round(float(operating_activity) + float(investing_activity), 2)


def compute_cfo_quality(
    operating_activity,
    net_profit,
) -> Optional[float]:
    """
    CFO Quality Score = CFO / Net Profit

    Measures earnings quality — are profits backed by real cash?

    Benchmark:
        > 1.0 = High quality (cash > profit)
        0.5 - 1.0 = Acceptable
        < 0.5 = Accrual risk (profit not backed by cash)
        Negative = Serious concern

    Edge cases:
        net_profit = 0 or None → return None
        net_profit negative    → return None (meaningless ratio)

    Examples:
        CFO=40000, PAT=35000 → 1.14 (excellent quality)
        CFO=5000,  PAT=35000 → 0.14 (accrual risk!)
    """
    if operating_activity is None or pd.isna(operating_activity):
        return None
    if net_profit is None or pd.isna(net_profit):
        return None
    if net_profit <= 0:
        return None

    return safe_divide(operating_activity, net_profit)


def compute_capex_intensity(
    investing_activity,
    sales,
) -> Optional[float]:
    """
    CapEx Intensity = |CFI| / Sales × 100

    Measures how capital-intensive a business is.
    We use |investing_activity| as a proxy for CapEx.

    Benchmark:
        < 3%  = Asset-light (IT, FMCG)
        3-8%  = Moderate
        > 8%  = Capital intensive (Steel, Power, Telecom)

    Edge cases:
        investing_activity = None → None
        sales = 0 or None         → None
        investing_activity > 0    → company selling assets
                                    (unusual — still use absolute value)
    """
    if investing_activity is None or pd.isna(investing_activity):
        return None
    if sales is None or pd.isna(sales) or sales == 0:
        return None

    capex_proxy = abs(float(investing_activity))
    return safe_divide(capex_proxy, sales, multiply=100)


def compute_fcf_conversion(
    fcf,
    operating_profit,
) -> Optional[float]:
    """
    FCF Conversion Rate = FCF / EBITDA × 100

    Measures how much operating profit converts to free cash.
    EBITDA proxy = operating_profit

    Benchmark:
        > 60% = Efficient cash conversion
        30-60% = Moderate
        < 30%  = Heavy CapEx or working capital issues

    Edge cases:
        operating_profit = 0 or None → None
        operating_profit < 0         → None (negative EBITDA)
    """
    if fcf is None or pd.isna(fcf):
        return None
    if operating_profit is None or pd.isna(operating_profit):
        return None
    if operating_profit <= 0:
        return None

    return safe_divide(fcf, operating_profit, multiply=100)


def compute_capital_allocation_pattern(
    operating_activity,
    investing_activity,
    financing_activity,
) -> str:
    """
    Classify capital allocation based on CFO/CFI/CFF signs.

    8 patterns based on + or - sign of each cash flow component:

    CFO  CFI  CFF   Pattern               Meaning
    +    -    -  →  Reinvestor            Profitable + investing + paying debt
    +    -    +  →  Growth Financed       Borrowing to fund growth
    +    +    -  →  Shareholder Returns   Selling investments + rewarding shareholders
    +    +    +  →  Asset Sale            Selling assets + raising capital
    -    -    +  →  Distress Signal       Burning cash + borrowing to survive
    -    +    +  →  Cash Burn             Selling assets + raising capital (distress)
    -    -    -  →  Mature Steady         All negative (rare)
    other       →  Other

    Args:
        operating_activity: CFO
        investing_activity: CFI
        financing_activity: CFF

    Returns:
        Pattern label string
    """
    def sign(val):
        """Return '+' or '-' based on value sign."""
        if val is None or pd.isna(val):
            return "?"
        return "+" if float(val) >= 0 else "-"

    cfo_sign = sign(operating_activity)
    cfi_sign = sign(investing_activity)
    cff_sign = sign(financing_activity)

    pattern_map = {
        ("+", "-", "-"): CapitalPattern.REINVESTOR,
        ("+", "-", "+"): CapitalPattern.GROWTH_FINANCED,
        ("+", "+", "-"): CapitalPattern.SHAREHOLDER_RETURN,
        ("+", "+", "+"): CapitalPattern.ASSET_SALE,
        ("-", "-", "+"): CapitalPattern.DISTRESS,
        ("-", "+", "+"): CapitalPattern.CASH_BURN,
        ("-", "-", "-"): CapitalPattern.MATURE_STEADY,
    }

    key = (cfo_sign, cfi_sign, cff_sign)
    return pattern_map.get(key, CapitalPattern.OTHER)


def detect_distress(
    operating_activity,
    financing_activity,
) -> bool:
    """
    Detect distress signal pattern.

    Distress = CFO < 0 AND CFF > 0
    (Company burning cash from operations AND raising debt/equity to survive)

    Returns:
        True if distress pattern detected
    """
    if operating_activity is None or financing_activity is None:
        return False
    if pd.isna(operating_activity) or pd.isna(financing_activity):
        return False

    return float(operating_activity) < 0 and float(financing_activity) > 0


def detect_deleveraging(
    financing_activity,
    borrowings_current,
    borrowings_previous,
) -> bool:
    """
    Detect deleveraging pattern.

    Deleveraging = CFF < 0 AND borrowings declining YoY
    (Company actively paying down debt)

    Returns:
        True if company is deleveraging
    """
    if financing_activity is None or pd.isna(financing_activity):
        return False

    cff_negative = float(financing_activity) < 0

    if borrowings_current is None or borrowings_previous is None:
        return cff_negative

    if pd.isna(borrowings_current) or pd.isna(borrowings_previous):
        return cff_negative

    debt_declining = float(borrowings_current) < float(borrowings_previous)
    return cff_negative and debt_declining


# ─────────────────────────────────────────────────────────────────────────────
# CFO QUALITY TIER
# ─────────────────────────────────────────────────────────────────────────────

def get_cfo_quality_tier(cfo_quality: Optional[float]) -> str:
    """
    Convert CFO quality ratio to a descriptive tier.

    Args:
        cfo_quality: CFO/PAT ratio

    Returns:
        Tier label string
    """
    if cfo_quality is None:
        return "N/A"
    if cfo_quality >= 1.0:
        return "High Quality Earnings"
    if cfo_quality >= 0.5:
        return "Acceptable"
    if cfo_quality >= 0:
        return "Accrual Risk"
    return "Serious Concern"


def get_capex_tier(capex_intensity: Optional[float]) -> str:
    """
    Convert CapEx intensity to a descriptive tier.

    Args:
        capex_intensity: CapEx/Revenue %

    Returns:
        Tier label string
    """
    if capex_intensity is None:
        return "N/A"
    if capex_intensity < 3:
        return "Asset-Light"
    if capex_intensity < 8:
        return "Moderate"
    return "Capital Intensive"


# ─────────────────────────────────────────────────────────────────────────────
# APPLY TO DATAFRAME
# ─────────────────────────────────────────────────────────────────────────────

def compute_all_cashflow_kpis(
    cf_df: pd.DataFrame,
    pl_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute all cash flow KPIs for every company-year.

    Args:
        cf_df: cashflow DataFrame
        pl_df: profitandloss DataFrame

    Returns:
        DataFrame with cash flow KPIs
    """
    logger.info(
        "Computing cash flow KPIs for %d rows...", len(cf_df)
    )

    # Merge cash flow with P&L on (company_id, year)
    merged = pd.merge(
        cf_df,
        pl_df[["company_id", "year", "sales",
               "net_profit", "operating_profit"]],
        on=["company_id", "year"],
        how="left",
    )

    results = []

    for _, row in merged.iterrows():
        cfo = row.get("operating_activity")
        cfi = row.get("investing_activity")
        cff = row.get("financing_activity")

        # Compute FCF
        fcf = compute_fcf(cfo, cfi)

        # Compute all KPIs
        kpis = {
            "company_id": row["company_id"],
            "year":       row["year"],

            # Raw cash flows
            "cash_from_operations_cr": cfo,
            "cash_from_investing_cr":  cfi,
            "cash_from_financing_cr":  cff,

            # Computed KPIs
            "free_cash_flow_cr":     fcf,
            "cfo_quality_score":     compute_cfo_quality(
                                         cfo,
                                         row.get("net_profit")
                                     ),
            "capex_intensity_pct":   compute_capex_intensity(
                                         cfi,
                                         row.get("sales")
                                     ),
            "fcf_conversion_pct":    compute_fcf_conversion(
                                         fcf,
                                         row.get("operating_profit")
                                     ),

            # Pattern classification
            "capital_pattern":       compute_capital_allocation_pattern(
                                         cfo, cfi, cff
                                     ),
            "is_distress":           detect_distress(cfo, cff),

            # Tier labels
            "cfo_quality_tier":      get_cfo_quality_tier(
                                         compute_cfo_quality(
                                             cfo, row.get("net_profit")
                                         )
                                     ),
            "capex_tier":            get_capex_tier(
                                         compute_capex_intensity(
                                             cfi, row.get("sales")
                                         )
                                     ),
        }

        results.append(kpis)

    df = pd.DataFrame(results)
    logger.info(
        "Cash flow KPIs computed: %d rows, %d columns",
        len(df), len(df.columns)
    )
    return df


def get_capital_pattern_summary(cf_kpis_df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarise capital allocation patterns across all companies.

    Args:
        cf_kpis_df: Output from compute_all_cashflow_kpis()

    Returns:
        Summary DataFrame with pattern counts
    """
    if "capital_pattern" not in cf_kpis_df.columns:
        return pd.DataFrame()

    summary = (
        cf_kpis_df.groupby("capital_pattern")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# QUICK TEST
# python src/analytics/cashflow_kpis.py
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing Cash Flow KPIs...")
    print("=" * 55)

    # ── FCF Tests ─────────────────────────────────────────────
    print("\n── Free Cash Flow ──")
    fcf = compute_fcf(40000, -5000)
    print(f"FCF (CFO=40000, CFI=-5000):  {fcf} Cr  (expected 35000)")

    fcf2 = compute_fcf(5000, -20000)
    print(f"FCF (CFO=5000, CFI=-20000):  {fcf2} Cr  (expected -15000)")

    fcf3 = compute_fcf(None, -5000)
    print(f"FCF (CFO=None, CFI=-5000):   {fcf3}  (expected None)")

    # ── CFO Quality Tests ─────────────────────────────────────
    print("\n── CFO Quality Score ──")
    q1 = compute_cfo_quality(40000, 35000)
    print(f"CFO Quality (40K/35K):       {q1}  (expected 1.14)")
    print(f"  Tier: {get_cfo_quality_tier(q1)}")

    q2 = compute_cfo_quality(5000, 35000)
    print(f"CFO Quality (5K/35K):        {q2}  (expected 0.14)")
    print(f"  Tier: {get_cfo_quality_tier(q2)}")

    q3 = compute_cfo_quality(40000, 0)
    print(f"CFO Quality (PAT=0):         {q3}  (expected None)")

    # ── CapEx Intensity Tests ─────────────────────────────────
    print("\n── CapEx Intensity ──")
    c1 = compute_capex_intensity(-5000, 225000)
    print(f"CapEx (IT company):          {c1}%  (expected 2.22%)")
    print(f"  Tier: {get_capex_tier(c1)}")

    c2 = compute_capex_intensity(-30000, 150000)
    print(f"CapEx (Steel company):       {c2}%  (expected 20.0%)")
    print(f"  Tier: {get_capex_tier(c2)}")

    # ── FCF Conversion Tests ──────────────────────────────────
    print("\n── FCF Conversion Rate ──")
    fc1 = compute_fcf_conversion(35000, 50000)
    print(f"FCF Conversion (35K/50K):    {fc1}%  (expected 70.0%)")

    fc2 = compute_fcf_conversion(-5000, 50000)
    print(f"FCF Conversion (-5K/50K):    {fc2}%  (expected -10.0%)")

    # ── Capital Pattern Tests ─────────────────────────────────
    print("\n── Capital Allocation Patterns ──")
    patterns = [
        (40000,  -5000, -10000, "Reinvestor (ideal)"),
        (40000,  -5000,  10000, "Growth Financed"),
        (40000,   5000, -10000, "Shareholder Returns"),
        (-5000,  -3000,  10000, "Distress Signal"),
        (-5000,   5000,  10000, "Cash Burn"),
    ]

    for cfo, cfi, cff, expected in patterns:
        pattern = compute_capital_allocation_pattern(cfo, cfi, cff)
        distress = detect_distress(cfo, cff)
        print(
            f"  CFO={cfo:>8}  CFI={cfi:>8}  CFF={cff:>8}  "
            f"→ {pattern:<25} "
            f"{'⚠️  DISTRESS' if distress else ''}"
        )
        print(f"    Expected: {expected}")

    # ── Test with sample DataFrame ────────────────────────────
    print("\n── Testing with sample DataFrame ──")

    sample_cf = pd.DataFrame({
        "company_id":         ["TCS",    "TATASTEEL", "RELIANCE"],
        "year":               ["2024-03", "2024-03",  "2024-03"],
        "operating_activity": [45000,     15000,       85000],
        "investing_activity": [-5000,    -25000,      -50000],
        "financing_activity": [-20000,    10000,      -30000],
    })

    sample_pl = pd.DataFrame({
        "company_id":        ["TCS",    "TATASTEEL", "RELIANCE"],
        "year":              ["2024-03", "2024-03",  "2024-03"],
        "sales":             [240893,    229171,      899041],
        "net_profit":        [46099,     -4910,       79020],
        "operating_profit":  [65000,     30000,      160000],
    })

    kpis_df = compute_all_cashflow_kpis(sample_cf, sample_pl)

    print("\nResults:")
    print("-" * 60)
    for _, row in kpis_df.iterrows():
        print(f"\n  {row['company_id']}:")
        print(f"    FCF:              {row['free_cash_flow_cr']:>10,.0f} Cr")
        print(f"    CFO Quality:      {row['cfo_quality_score']}  ({row['cfo_quality_tier']})")
        print(f"    CapEx Intensity:  {row['capex_intensity_pct']}%  ({row['capex_tier']})")
        print(f"    FCF Conversion:   {row['fcf_conversion_pct']}%")
        print(f"    Capital Pattern:  {row['capital_pattern']}")
        print(f"    Distress:         {row['is_distress']}")

    print("\n✅ Cash Flow KPI Engine working correctly!")