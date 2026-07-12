"""
ratio_engine.py — Master Ratio Engine

Reads P&L, Balance Sheet and Cash Flow from SQLite.
Computes all 50+ KPIs using ratios.py, cagr.py, cashflow_kpis.py.
Saves results to financial_ratios table in SQLite.
Also generates capital_allocation.csv and ratio_edge_cases.log.

Run with:
    python src/analytics/ratio_engine.py
    OR
    make ratios

Author: Samadhan
Sprint: 2 — Day 11
"""

import sqlite3
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import DB_PATH, OUTPUT_PATH
from src.analytics.ratios import (
    compute_npm, compute_opm, compute_ebit_margin,
    compute_roe, compute_roce, compute_roa,
    compute_de_ratio, compute_icr,
    compute_asset_turnover, compute_net_debt,
)
from src.analytics.cagr import compute_all_cagrs
from src.analytics.cashflow_kpis import (
    compute_all_cashflow_kpis,
    compute_capital_allocation_pattern,
    detect_distress,
    get_cfo_quality_tier,
    get_capex_tier,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Edge case log
edge_cases = []


def log_edge_case(company_id, year, kpi, reason):
    """Record an edge case for logging."""
    edge_cases.append({
        "company_id": company_id,
        "year":       year,
        "kpi":        kpi,
        "reason":     reason,
        "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA FROM DATABASE
# ─────────────────────────────────────────────────────────────────────────────

def load_from_db() -> tuple:
    """
    Load P&L, Balance Sheet and Cash Flow from SQLite.

    Returns:
        Tuple of (pl_df, bs_df, cf_df)
    """
    logger.info("Loading data from database: %s", DB_PATH)

    with sqlite3.connect(DB_PATH) as conn:
        pl_df = pd.read_sql(
            "SELECT * FROM profitandloss ORDER BY company_id, year",
            conn
        )
        bs_df = pd.read_sql(
            "SELECT * FROM balancesheet ORDER BY company_id, year",
            conn
        )
        cf_df = pd.read_sql(
            "SELECT * FROM cashflow ORDER BY company_id, year",
            conn
        )

    logger.info(
        "Loaded: P&L=%d rows, BS=%d rows, CF=%d rows",
        len(pl_df), len(bs_df), len(cf_df)
    )
    return pl_df, bs_df, cf_df


# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE PROFITABILITY + LEVERAGE KPIs
# ─────────────────────────────────────────────────────────────────────────────

def compute_base_ratios(pl_df: pd.DataFrame, bs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute profitability and leverage KPIs for every company-year.

    Merges P&L + BS and computes:
    NPM, OPM, EBIT Margin, ROE, ROCE, ROA,
    D/E, ICR, Asset Turnover, Net Debt

    Returns:
        DataFrame with base ratios
    """
    logger.info("Computing base ratios (profitability + leverage)...")

    merged = pd.merge(
        pl_df, bs_df,
        on=["company_id", "year"],
        how="inner",
        suffixes=("_pl", "_bs"),
    )
    logger.info("Merged P&L + BS: %d rows", len(merged))

    results = []

    for _, row in merged.iterrows():
        cid  = row["company_id"]
        year = row["year"]

        # Profitability
        npm   = compute_npm(row.get("net_profit"), row.get("sales"))
        opm   = compute_opm(row.get("operating_profit"), row.get("sales"))
        ebit  = compute_ebit_margin(
                    row.get("operating_profit"),
                    row.get("depreciation"),
                    row.get("sales")
                )
        roe   = compute_roe(
                    row.get("net_profit"),
                    row.get("equity_capital"),
                    row.get("reserves")
                )
        roce  = compute_roce(
                    row.get("operating_profit"),
                    row.get("depreciation"),
                    row.get("equity_capital"),
                    row.get("reserves"),
                    row.get("borrowings")
                )
        roa   = compute_roa(row.get("net_profit"), row.get("total_assets"))

        # Leverage
        de    = compute_de_ratio(
                    row.get("borrowings"),
                    row.get("equity_capital"),
                    row.get("reserves"),
                    company_id=cid
                )
        icr   = compute_icr(
                    row.get("operating_profit"),
                    row.get("other_income"),
                    row.get("interest"),
                    company_id=cid
                )
        at    = compute_asset_turnover(
                    row.get("sales"),
                    row.get("total_assets")
                )
        nd    = compute_net_debt(
                    row.get("borrowings"),
                    row.get("investments")
                )

        # Log edge cases
        if roe is None:
            eq  = row.get("equity_capital", 0) or 0
            res = row.get("reserves", 0) or 0
            if (eq + res) <= 0:
                log_edge_case(cid, year, "ROE", "Negative/zero equity")

        if icr is None:
            interest = row.get("interest", 0) or 0
            if interest == 0:
                log_edge_case(cid, year, "ICR", "Debt-free company")

        if de is not None and de > 5:
            log_edge_case(
                cid, year, "D/E",
                f"High leverage D/E={de} — check if financial company"
            )

        results.append({
            "company_id":                  cid,
            "year":                        year,

            # Profitability KPIs
            "net_profit_margin_pct":       npm,
            "operating_profit_margin_pct": opm,
            "ebit_margin_pct":             ebit,
            "return_on_equity_pct":        roe,
            "return_on_capital_pct":       roce,
            "return_on_assets_pct":        roa,

            # Leverage KPIs
            "debt_to_equity":              de,
            "interest_coverage":           icr,
            "asset_turnover":              at,
            "net_debt_cr":                 nd,

            # Raw values for CAGR computation
            "sales_cr":                    row.get("sales"),
            "net_profit_cr":               row.get("net_profit"),
            "eps":                         row.get("eps"),
            "total_debt_cr":               row.get("borrowings"),
            "dividend_payout_ratio_pct":   row.get("dividend_payout"),
            "book_value_per_share":        None,  # computed separately
        })

    df = pd.DataFrame(results)
    logger.info("Base ratios computed: %d rows", len(df))
    return df


# ─────────────────────────────────────────────────────────────────────────────
# MERGE ALL KPIs INTO FINAL TABLE
# ─────────────────────────────────────────────────────────────────────────────

def build_financial_ratios_table(
    pl_df: pd.DataFrame,
    bs_df: pd.DataFrame,
    cf_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the complete financial_ratios DataFrame by combining:
    - Base ratios (profitability + leverage)
    - CAGR values (revenue, PAT, EPS)
    - Cash flow KPIs (FCF, CFO quality, capital patterns)

    Returns:
        Complete financial_ratios DataFrame
    """
    logger.info("Building complete financial_ratios table...")

    # ── Step 1: Base ratios ───────────────────────────────────────────────
    base_df = compute_base_ratios(pl_df, bs_df)

    # ── Step 2: CAGR (one row per company — latest year values) ──────────
    logger.info("Computing CAGR values...")
    cagr_df = compute_all_cagrs(pl_df)

    # Merge CAGR into base ratios
    # CAGR is computed per company (not per year) — attach to each row
    merged = pd.merge(
        base_df,
        cagr_df[[
            "company_id",
            "revenue_cagr_3yr",  "revenue_cagr_3yr_flag",
            "revenue_cagr_5yr",  "revenue_cagr_5yr_flag",
            "revenue_cagr_10yr", "revenue_cagr_10yr_flag",
            "pat_cagr_3yr",      "pat_cagr_3yr_flag",
            "pat_cagr_5yr",      "pat_cagr_5yr_flag",
            "pat_cagr_10yr",     "pat_cagr_10yr_flag",
            "eps_cagr_3yr",      "eps_cagr_3yr_flag",
            "eps_cagr_5yr",      "eps_cagr_5yr_flag",
        ]],
        on="company_id",
        how="left",
    )

    logger.info("After CAGR merge: %d rows", len(merged))

    # ── Step 3: Cash flow KPIs ────────────────────────────────────────────
    logger.info("Computing cash flow KPIs...")
    cf_kpis_df = compute_all_cashflow_kpis(cf_df, pl_df)

    # Merge cash flow KPIs
    merged = pd.merge(
        merged,
        cf_kpis_df[[
            "company_id", "year",
            "free_cash_flow_cr",
            "cash_from_operations_cr",
            "cfo_quality_score",
            "capex_intensity_pct",
            "fcf_conversion_pct",
            "capital_pattern",
            "is_distress",
            "cfo_quality_tier",
            "capex_tier",
        ]],
        on=["company_id", "year"],
        how="left",
    )

    logger.info("Final financial_ratios table: %d rows, %d columns",
                len(merged), len(merged.columns))
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# SAVE TO DATABASE
# ─────────────────────────────────────────────────────────────────────────────

def save_to_database(df: pd.DataFrame) -> int:
    """
    Save financial_ratios DataFrame to SQLite.

    Replaces existing data with fresh computation.

    Returns:
        Number of rows saved
    """
    logger.info("Saving %d rows to financial_ratios table...", len(df))

    try:
        with sqlite3.connect(DB_PATH) as conn:
            # First add new columns to financial_ratios table
            # if they don't exist (safe to run multiple times)
            existing_cols_query = "PRAGMA table_info(financial_ratios)"
            existing = pd.read_sql(existing_cols_query, conn)
            existing_col_names = existing["name"].tolist()

            # Add columns that are in df but not in table
            df_cols = df.columns.tolist()
            for col in df_cols:
                if col not in existing_col_names and col not in ["id"]:
                    try:
                        conn.execute(
                            f"ALTER TABLE financial_ratios ADD COLUMN {col} REAL"
                        )
                    except Exception:
                        pass

            conn.commit()

        # Now save data — replace existing
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM financial_ratios")
            conn.commit()

            chunk_size = 200
            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i:i + chunk_size]
                chunk.to_sql(
                    "financial_ratios",
                    conn,
                    if_exists="append",
                    index=False,
                )
            conn.commit()

            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM financial_ratios")
            count = cursor.fetchone()[0]

        logger.info("Saved %d rows to financial_ratios table", count)
        return count

    except Exception as e:
        logger.error("Failed to save financial_ratios: %s", e)
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# SAVE CAPITAL ALLOCATION CSV
# ─────────────────────────────────────────────────────────────────────────────

def save_capital_allocation(df: pd.DataFrame):
    """Save capital allocation patterns to CSV."""
    output_file = OUTPUT_PATH / "capital_allocation.csv"

    if "capital_pattern" not in df.columns:
        logger.warning("No capital_pattern column found")
        return

    cap_df = df[[
        "company_id", "year",
        "capital_pattern", "is_distress",
        "cfo_quality_tier", "capex_tier",
    ]].copy()

    cap_df.to_csv(output_file, index=False)
    logger.info(
        "Capital allocation saved: %d rows → %s",
        len(cap_df), output_file
    )

    # Print pattern summary
    print("\n── Capital Allocation Pattern Summary ──")
    summary = cap_df["capital_pattern"].value_counts()
    for pattern, count in summary.items():
        print(f"  {pattern:<30} {count:>4} rows")

    distress_count = cap_df["is_distress"].sum()
    print(f"\n  ⚠️  Distress signals detected: {distress_count} rows")


# ─────────────────────────────────────────────────────────────────────────────
# SAVE EDGE CASES LOG
# ─────────────────────────────────────────────────────────────────────────────

def save_edge_cases_log():
    """Save edge cases log to file."""
    log_file = OUTPUT_PATH / "ratio_edge_cases.log"

    if not edge_cases:
        log_file.write_text("No edge cases found.\n", encoding="utf-8")
        return

    lines = [
        "Ratio Engine Edge Cases Log",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total edge cases: {len(edge_cases)}",
        "=" * 60,
        "",
    ]

    for ec in edge_cases[:100]:  # Log first 100
        lines.append(
            f"[{ec['company_id']:<12}] [{ec['year']}] "
            f"KPI={ec['kpi']:<15} → {ec['reason']}"
        )

    if len(edge_cases) > 100:
        lines.append(f"\n... and {len(edge_cases) - 100} more")

    log_file.write_text("\n".join(lines), encoding="utf-8")
    logger.info(
        "Edge cases log saved: %d entries → %s",
        len(edge_cases), log_file
    )


# ─────────────────────────────────────────────────────────────────────────────
# VERIFY RESULTS
# ─────────────────────────────────────────────────────────────────────────────

def verify_results():
    """Quick verification of saved financial_ratios table."""
    print("\n" + "=" * 60)
    print("FINANCIAL RATIOS — VERIFICATION")
    print("=" * 60)

    with sqlite3.connect(DB_PATH) as conn:
        # Total rows
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM financial_ratios")
        total = cursor.fetchone()[0]
        print(f"\n  Total rows:     {total:,}")

        # Companies covered
        cursor.execute(
            "SELECT COUNT(DISTINCT company_id) FROM financial_ratios"
        )
        companies = cursor.fetchone()[0]
        print(f"  Companies:      {companies}")

        # Sample — TCS latest year
        tcs = pd.read_sql("""
            SELECT company_id, year,
                   net_profit_margin_pct,
                   return_on_equity_pct,
                   return_on_capital_pct,
                   debt_to_equity,
                   free_cash_flow_cr,
                   capital_pattern
            FROM financial_ratios
            WHERE company_id = 'TCS'
            ORDER BY year DESC
            LIMIT 3
        """, conn)

        if not tcs.empty:
            print("\n  TCS — Latest 3 Years:")
            print("-" * 55)
            for _, row in tcs.iterrows():
                print(
                    f"  {row['year']}  "
                    f"NPM={row['net_profit_margin_pct']}%  "
                    f"ROE={row['return_on_equity_pct']}%  "
                    f"D/E={row['debt_to_equity']}  "
                    f"Pattern={row['capital_pattern']}"
                )

        # Sample — RELIANCE latest year
        rel = pd.read_sql("""
            SELECT company_id, year,
                   net_profit_margin_pct,
                   return_on_equity_pct,
                   debt_to_equity,
                   free_cash_flow_cr
            FROM financial_ratios
            WHERE company_id = 'RELIANCE'
            ORDER BY year DESC
            LIMIT 1
        """, conn)

        if not rel.empty:
            print("\n  RELIANCE — Latest Year:")
            print("-" * 55)
            row = rel.iloc[0]
            print(
                f"  {row['year']}  "
                f"NPM={row['net_profit_margin_pct']}%  "
                f"ROE={row['return_on_equity_pct']}%  "
                f"D/E={row['debt_to_equity']}  "
                f"FCF={row['free_cash_flow_cr']:,.0f} Cr"
            )

        # CAGR check
        cagr = pd.read_sql("""
            SELECT company_id,
                   revenue_cagr_3yr,
                   revenue_cagr_5yr,
                   revenue_cagr_10yr
            FROM financial_ratios
            WHERE company_id = 'TCS'
            LIMIT 1
        """, conn)

        if not cagr.empty:
            row = cagr.iloc[0]
            print(f"\n  TCS Revenue CAGR:")
            print(f"    3yr:  {row['revenue_cagr_3yr']}%")
            print(f"    5yr:  {row['revenue_cagr_5yr']}%")
            print(f"    10yr: {row['revenue_cagr_10yr']}%")

    print("\n" + "=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_ratio_engine():
    """Run the complete ratio engine pipeline."""
    start_time = datetime.now()

    print("=" * 60)
    print("Nifty 100 — Financial Ratio Engine")
    print("=" * 60)

    # ── Step 1: Load data ─────────────────────────────────────────────────
    pl_df, bs_df, cf_df = load_from_db()

    # ── Step 2: Compute all KPIs ──────────────────────────────────────────
    ratios_df = build_financial_ratios_table(pl_df, bs_df, cf_df)

    # ── Step 3: Save to database ──────────────────────────────────────────
    rows_saved = save_to_database(ratios_df)

    # ── Step 4: Save capital allocation CSV ───────────────────────────────
    save_capital_allocation(ratios_df)

    # ── Step 5: Save edge cases log ───────────────────────────────────────
    save_edge_cases_log()

    # ── Step 6: Verify results ────────────────────────────────────────────
    verify_results()

    # ── Done ──────────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start_time).total_seconds()

    print(f"\n✅ Ratio Engine complete in {elapsed:.1f} seconds")
    print(f"📊 Rows saved:          {rows_saved:,}")
    print(f"⚠️  Edge cases logged:   {len(edge_cases)}")
    print(f"📄 Capital allocation:  {OUTPUT_PATH / 'capital_allocation.csv'}")
    print(f"📄 Edge cases log:      {OUTPUT_PATH / 'ratio_edge_cases.log'}")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_ratio_engine()