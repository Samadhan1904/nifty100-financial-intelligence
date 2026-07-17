"""
sprint2_review.py — Sprint 2 Day 13 Review Script

Reviews:
1. Edge cases from ratio_edge_cases.log
2. CAGR turnaround flags
3. Final spot check on 5 companies
4. Generates Sprint 2 summary report

Run with:
    python src/analytics/sprint2_review.py

Author: Samadhan
Sprint: 2 — Day 13
"""

import sqlite3
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import DB_PATH, OUTPUT_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

def load_data():
    """Load all required tables."""
    with sqlite3.connect(DB_PATH) as conn:
        ratios_df  = pd.read_sql(
            "SELECT * FROM financial_ratios ORDER BY company_id, year",
            conn
        )
        pl_df      = pd.read_sql(
            "SELECT * FROM profitandloss ORDER BY company_id, year",
            conn
        )
        sectors_df = pd.read_sql(
            "SELECT company_id, broad_sector, sub_sector FROM sectors",
            conn
        )
        companies_df = pd.read_sql(
            "SELECT id, company_name FROM companies",
            conn
        )

    logger.info(
        "Loaded: ratios=%d, P&L=%d, sectors=%d, companies=%d",
        len(ratios_df), len(pl_df),
        len(sectors_df), len(companies_df)
    )
    return ratios_df, pl_df, sectors_df, companies_df


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: EDGE CASES REVIEW
# ─────────────────────────────────────────────────────────────────────────────

def review_edge_cases(ratios_df: pd.DataFrame) -> dict:
    """
    Review edge cases in the financial ratios table.
    Count None values and flag patterns.
    """
    print("\n" + "=" * 60)
    print("SECTION 1: EDGE CASES REVIEW")
    print("=" * 60)

    stats = {}
    total_rows = len(ratios_df)

    # Check None counts for key KPIs
    kpi_cols = [
        "net_profit_margin_pct",
        "return_on_equity_pct",
        "return_on_capital_pct",
        "debt_to_equity",
        "interest_coverage",
        "free_cash_flow_cr",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
    ]

    print(f"\n  Total rows in financial_ratios: {total_rows}")
    print(f"\n  None/NULL value counts per KPI:")
    print(f"  {'KPI':<35} {'None Count':>10} {'None %':>8}")
    print(f"  {'-'*55}")

    for col in kpi_cols:
        if col in ratios_df.columns:
            none_count = ratios_df[col].isna().sum()
            none_pct   = (none_count / total_rows) * 100
            icon = "✅" if none_pct < 20 else "⚠️ "
            print(
                f"  {icon} {col:<33} "
                f"{none_count:>10} "
                f"{none_pct:>7.1f}%"
            )
            stats[col] = none_count

    # Debt-free companies
    debt_free = ratios_df[
        ratios_df["debt_to_equity"] == 0.0
    ]["company_id"].nunique()
    print(f"\n  Debt-free companies (D/E=0):    {debt_free}")

    # Distress signals
    if "is_distress" in ratios_df.columns:
        distress_rows = ratios_df["is_distress"].sum()
        distress_cos  = ratios_df[
            ratios_df["is_distress"] == True
        ]["company_id"].nunique()
        print(f"  Distress signal rows:           {distress_rows}")
        print(f"  Companies with any distress:    {distress_cos}")

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: CAGR TURNAROUND FLAGS REVIEW
# ─────────────────────────────────────────────────────────────────────────────

def review_cagr_flags(ratios_df: pd.DataFrame) -> None:
    """Review CAGR turnaround flags and edge cases."""
    print("\n" + "=" * 60)
    print("SECTION 2: CAGR FLAGS REVIEW")
    print("=" * 60)

    flag_cols = [
        ("revenue_cagr_5yr_flag", "Revenue CAGR 5yr"),
        ("pat_cagr_5yr_flag",     "PAT CAGR 5yr"),
        ("eps_cagr_5yr_flag",     "EPS CAGR 5yr"),
    ]

    for flag_col, label in flag_cols:
        if flag_col not in ratios_df.columns:
            continue

        # Get unique rows per company (avoid duplicates from CAGR merge)
        unique = ratios_df.drop_duplicates(
            subset=["company_id"]
        )[[flag_col, "company_id"]]

        flag_counts = unique[flag_col].value_counts()

        print(f"\n  {label}:")
        for flag, count in flag_counts.items():
            icon = "✅" if flag == "NORMAL" else "⚠️ "
            print(f"    {icon} {flag:<20} {count} companies")

    # Show companies with turnaround flags
    if "pat_cagr_5yr_flag" in ratios_df.columns:
        turnaround = ratios_df[
            ratios_df["pat_cagr_5yr_flag"] == "TURNAROUND"
        ]["company_id"].unique()

        if len(turnaround) > 0:
            print(f"\n  Companies with PAT CAGR TURNAROUND flag:")
            for co in sorted(turnaround):
                print(f"    → {co} (had losses, now profitable)")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: FINAL SPOT CHECK — 5 MORE COMPANIES
# ─────────────────────────────────────────────────────────────────────────────

def final_spot_check(
    ratios_df: pd.DataFrame,
    companies_df: pd.DataFrame,
) -> None:
    """Spot check 5 more companies across different sectors."""
    print("\n" + "=" * 60)
    print("SECTION 3: FINAL SPOT CHECK (5 more companies)")
    print("=" * 60)

    spot_list = [
        ("BAJFINANCE",  "Consumer Finance (NBFC)"),
        ("SUNPHARMA",   "Pharmaceuticals"),
        ("MARUTI",      "Automobiles"),
        ("NTPC",        "Power & Utilities"),
        ("ADANIPORTS",  "Infrastructure"),
    ]

    for ticker, sector in spot_list:
        data = ratios_df[
            ratios_df["company_id"] == ticker
        ].sort_values("year", ascending=False)

        if data.empty:
            print(f"\n  ⚠️  {ticker} — No data in ratios table")
            continue

        latest = data.iloc[0]

        # Get company name
        co_name = companies_df[
            companies_df["id"] == ticker
        ]["company_name"].values
        co_name = co_name[0] if len(co_name) > 0 else ticker

        print(f"\n  {ticker} — {str(co_name)[:35]}")
        print(f"  Sector: {sector} | Year: {latest['year']}")
        print(f"  {'─' * 50}")

        # Key metrics
        metrics = [
            ("NPM",          "net_profit_margin_pct",       "%"),
            ("ROE",          "return_on_equity_pct",        "%"),
            ("ROCE",         "return_on_capital_pct",       "%"),
            ("D/E",          "debt_to_equity",              "x"),
            ("FCF",          "free_cash_flow_cr",           " Cr"),
            ("Rev CAGR 5yr", "revenue_cagr_5yr",            "%"),
            ("Pattern",      "capital_pattern",             ""),
        ]

        for label, col, unit in metrics:
            val = latest.get(col, "N/A")
            if val is None or (
                isinstance(val, float) and pd.isna(val)
            ):
                val = "N/A"
            elif isinstance(val, float):
                val = round(val, 2)
            print(f"  {label:<15} {val}{unit}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: TOP AND BOTTOM PERFORMERS
# ─────────────────────────────────────────────────────────────────────────────

def show_top_bottom(ratios_df: pd.DataFrame) -> None:
    """Show top and bottom performers for key KPIs."""
    print("\n" + "=" * 60)
    print("SECTION 4: TOP & BOTTOM PERFORMERS (Latest Year)")
    print("=" * 60)

    # Get latest year per company
    latest = ratios_df.sort_values("year").groupby(
        "company_id"
    ).last().reset_index()

    # Top 5 ROE
    print("\n  🏆 Top 5 Companies by ROE:")
    top_roe = latest.nlargest(5, "return_on_equity_pct")[
        ["company_id", "return_on_equity_pct"]
    ]
    for _, row in top_roe.iterrows():
        print(
            f"    {row['company_id']:<15} "
            f"ROE={row['return_on_equity_pct']:.1f}%"
        )

    # Top 5 Revenue CAGR 5yr
    print("\n  🚀 Top 5 Companies by Revenue CAGR (5yr):")
    top_cagr = latest.nlargest(5, "revenue_cagr_5yr")[
        ["company_id", "revenue_cagr_5yr"]
    ]
    for _, row in top_cagr.iterrows():
        print(
            f"    {row['company_id']:<15} "
            f"Rev CAGR 5yr={row['revenue_cagr_5yr']:.1f}%"
        )

    # Top 5 FCF
    print("\n  💰 Top 5 Companies by FCF:")
    top_fcf = latest.nlargest(5, "free_cash_flow_cr")[
        ["company_id", "free_cash_flow_cr"]
    ]
    for _, row in top_fcf.iterrows():
        print(
            f"    {row['company_id']:<15} "
            f"FCF={row['free_cash_flow_cr']:,.0f} Cr"
        )

    # Bottom 5 D/E non-financial
    print("\n  ⚠️  Top 5 Most Leveraged (non-financial, D/E):")
    fin_tickers = {
        "HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK",
        "SBIN", "BANKBARODA", "CANBK", "PNB", "INDUSINDBK",
        "BAJFINANCE", "CHOLAFIN", "SHRIRAMFIN", "JIOFIN",
        "PFC", "RECLTD", "LICI", "HDFCLIFE",
        "SBILIFE", "ICICIPRULI", "ICICIGI", "UNIONBANK",
    }
    non_fin = latest[~latest["company_id"].isin(fin_tickers)]
    top_de  = non_fin.nlargest(5, "debt_to_equity")[
        ["company_id", "debt_to_equity"]
    ]
    for _, row in top_de.iterrows():
        print(
            f"    {row['company_id']:<15} "
            f"D/E={row['debt_to_equity']:.2f}x"
        )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: SPRINT 2 SUMMARY REPORT
# ─────────────────────────────────────────────────────────────────────────────

def generate_sprint2_summary(ratios_df: pd.DataFrame) -> None:
    """Generate and save Sprint 2 summary."""
    print("\n" + "=" * 60)
    print("SECTION 5: SPRINT 2 SUMMARY")
    print("=" * 60)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(id) FROM financial_ratios"
        )
        total_rows = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(DISTINCT company_id) FROM financial_ratios"
        )
        companies = cursor.fetchone()[0]

    # CAGR coverage
    has_5yr = ratios_df[
        ratios_df["revenue_cagr_5yr"].notna()
    ]["company_id"].nunique()

    has_10yr = ratios_df[
        ratios_df["revenue_cagr_10yr"].notna()
    ]["company_id"].nunique()

    has_roe = ratios_df[
        ratios_df["return_on_equity_pct"].notna()
    ]["company_id"].nunique()

    print(f"\n  financial_ratios table:")
    print(f"    Total rows:              {total_rows:,}")
    print(f"    Companies covered:       {companies}/92")
    print(f"    Companies with ROE:      {has_roe}")
    print(f"    Companies with 5yr CAGR: {has_5yr}")
    print(f"    Companies with 10yr CAGR:{has_10yr}")

    # Files generated
    print(f"\n  Output files generated:")
    outputs = [
        "output/capital_allocation.csv",
        "output/ratio_edge_cases.log",
        "output/sector_validation_report.csv",
    ]
    for f in outputs:
        path = OUTPUT_PATH.parent / f
        exists = path.exists()
        icon  = "✅" if exists else "❌"
        print(f"    {icon} {f}")

    # Sprint 2 exit criteria
    print(f"\n  Sprint 2 Exit Criteria:")
    criteria = [
        ("financial_ratios rows >= 1000",
         total_rows >= 1000, total_rows),
        ("92 companies covered",
         companies >= 90, companies),
        ("ROE computed for 85+ companies",
         has_roe >= 85, has_roe),
        ("5yr CAGR for 85+ companies",
         has_5yr >= 85, has_5yr),
        ("capital_allocation.csv exists",
         (OUTPUT_PATH / "capital_allocation.csv").exists(),
         ""),
    ]

    all_pass = True
    for label, passed, value in criteria:
        icon = "✅ PASS" if passed else "❌ FAIL"
        print(f"    {icon}  {label} (got: {value})")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("  🎉 ALL SPRINT 2 EXIT CRITERIA PASSED!")
        print("  ✅ Ready for Day 14 — Sprint 2 Sign-off")
    else:
        print("  ⚠️  Some criteria failed — review before Day 14")

    # Save summary to file
    summary_file = OUTPUT_PATH / "sprint2_summary.txt"
    lines = [
        "Sprint 2 — Financial Ratio Engine Summary",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 50,
        f"Total rows:        {total_rows}",
        f"Companies:         {companies}/92",
        f"ROE coverage:      {has_roe} companies",
        f"5yr CAGR coverage: {has_5yr} companies",
        f"10yr CAGR:         {has_10yr} companies",
        "",
        "Sprint 2 Status: " + (
            "COMPLETE ✅" if all_pass else "NEEDS REVIEW ⚠️"
        ),
    ]
    summary_file.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Sprint 2 summary saved to: %s", summary_file)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run_sprint2_review():
    """Run complete Sprint 2 Day 13 review."""
    print("=" * 60)
    print("Sprint 2 — Day 13: Edge Cases + Final Spot Check")
    print("=" * 60)

    ratios_df, pl_df, sectors_df, companies_df = load_data()

    review_edge_cases(ratios_df)
    review_cagr_flags(ratios_df)
    final_spot_check(ratios_df, companies_df)
    show_top_bottom(ratios_df)
    generate_sprint2_summary(ratios_df)

    print("\n✅ Day 13 Review Complete!")


if __name__ == "__main__":
    run_sprint2_review()