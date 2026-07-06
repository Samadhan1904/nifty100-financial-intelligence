"""
sprint1_verify.py — Final Sprint 1 Verification Script

Runs all 10 exploratory queries and checks all
Sprint 1 exit criteria. Generates sprint1_summary.txt

Run with:
    python src/etl/sprint1_verify.py

Author: Pranjal
Sprint: 1 — Day 7
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import DB_PATH, OUTPUT_PATH, PROJECT_ROOT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

QUERIES_FILE = PROJECT_ROOT / "notebooks" / "exploratory_queries.sql"


def get_conn():
    """Get SQLite connection with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def run_exploratory_queries():
    """Run all 10 SQL queries and print results."""
    lines = []

    def log(text=""):
        lines.append(text)
        print(text)

    log("=" * 65)
    log("SPRINT 1 — EXPLORATORY QUERIES")
    log(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 65)

    with get_conn() as conn:
        cursor = conn.cursor()

        # ── Query 1: Row counts ───────────────────────────────────────
        log("\n📊 QUERY 1: Row Count Per Table")
        log("-" * 40)
        cursor.execute("""
            SELECT 'companies'      AS tbl, COUNT(*) AS cnt FROM companies
            UNION ALL
            SELECT 'profitandloss', COUNT(*) FROM profitandloss
            UNION ALL
            SELECT 'balancesheet',  COUNT(*) FROM balancesheet
            UNION ALL
            SELECT 'cashflow',      COUNT(*) FROM cashflow
            UNION ALL
            SELECT 'analysis',      COUNT(*) FROM analysis
            UNION ALL
            SELECT 'documents',     COUNT(*) FROM documents
            UNION ALL
            SELECT 'prosandcons',   COUNT(*) FROM prosandcons
            UNION ALL
            SELECT 'sectors',       COUNT(*) FROM sectors
            UNION ALL
            SELECT 'stock_prices',  COUNT(*) FROM stock_prices
            UNION ALL
            SELECT 'market_cap',    COUNT(*) FROM market_cap
        """)
        total = 0
        for row in cursor.fetchall():
            icon = "✅" if row["cnt"] > 0 else "❌"
            log(f"  {icon} {row['tbl']:<25} {row['cnt']:>6} rows")
            total += row["cnt"]
        log(f"\n  Total: {total:,} rows")

        # ── Query 2: Year coverage ────────────────────────────────────
        log("\n📅 QUERY 2: Year Coverage Summary")
        log("-" * 40)
        cursor.execute("""
            SELECT
                COUNT(*) AS total_companies,
                SUM(CASE WHEN yr_count >= 10 THEN 1 ELSE 0 END) AS ge_10yr,
                SUM(CASE WHEN yr_count >= 5
                     AND yr_count < 10 THEN 1 ELSE 0 END)       AS ge_5yr,
                SUM(CASE WHEN yr_count < 5 THEN 1 ELSE 0 END)   AS lt_5yr,
                ROUND(AVG(yr_count), 1)                          AS avg_years
            FROM (
                SELECT company_id, COUNT(DISTINCT year) AS yr_count
                FROM profitandloss
                GROUP BY company_id
            )
        """)
        row = cursor.fetchone()
        log(f"  Total companies with P&L data: {row['total_companies']}")
        log(f"  Companies with 10+ years:      {row['ge_10yr']}")
        log(f"  Companies with 5-9 years:      {row['ge_5yr']}")
        log(f"  Companies with < 5 years:      {row['lt_5yr']} ⚠️")
        log(f"  Average years per company:     {row['avg_years']}")

        # ── Query 3: NULL check ───────────────────────────────────────
        log("\n🔍 QUERY 3: NULL Values in Critical Columns")
        log("-" * 40)
        null_checks = [
            ("P&L — sales",           "SELECT COUNT(*) FROM profitandloss WHERE sales IS NULL"),
            ("P&L — net_profit",      "SELECT COUNT(*) FROM profitandloss WHERE net_profit IS NULL"),
            ("P&L — eps",             "SELECT COUNT(*) FROM profitandloss WHERE eps IS NULL"),
            ("BS  — total_assets",    "SELECT COUNT(*) FROM balancesheet WHERE total_assets IS NULL"),
            ("BS  — borrowings",      "SELECT COUNT(*) FROM balancesheet WHERE borrowings IS NULL"),
            ("CF  — operating_activity","SELECT COUNT(*) FROM cashflow WHERE operating_activity IS NULL"),
        ]
        for label, query in null_checks:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            icon  = "✅" if count == 0 else "⚠️ "
            log(f"  {icon} {label:<30} {count} nulls")

        # ── Query 4: Top 10 by sales ──────────────────────────────────
        log("\n🏆 QUERY 4: Top 10 Companies by Latest Sales")
        log("-" * 40)
        cursor.execute("""
            SELECT
                p.company_id,
                p.year,
                ROUND(p.sales, 0)      AS sales_cr,
                ROUND(p.net_profit, 0) AS profit_cr,
                ROUND(p.opm_percentage, 1) AS opm_pct
            FROM profitandloss p
            WHERE p.year = (
                SELECT MAX(year) FROM profitandloss p2
                WHERE p2.company_id = p.company_id
            )
            ORDER BY p.sales DESC
            LIMIT 10
        """)
        for i, row in enumerate(cursor.fetchall(), 1):
            log(
                f"  {i:>2}. {row['company_id']:<12} "
                f"Sales: {row['sales_cr']:>10,.0f} Cr  "
                f"Profit: {row['profit_cr']:>8,.0f} Cr  "
                f"OPM: {row['opm_pct']}%"
            )

        # ── Query 5: Sector distribution ──────────────────────────────
        log("\n🏭 QUERY 5: Sector Distribution")
        log("-" * 40)
        cursor.execute("""
            SELECT broad_sector, COUNT(*) AS cnt
            FROM sectors
            GROUP BY broad_sector
            ORDER BY cnt DESC
        """)
        for row in cursor.fetchall():
            bar = "█" * row["cnt"]
            log(f"  {row['broad_sector']:<30} {row['cnt']:>3} {bar}")

        # ── Query 6: Debt-free companies ──────────────────────────────
        log("\n💰 QUERY 6: Debt-Free Companies (latest year)")
        log("-" * 40)
        cursor.execute("""
            SELECT b.company_id, b.year, b.borrowings,
                   s.broad_sector
            FROM balancesheet b
            JOIN sectors s ON b.company_id = s.company_id
            WHERE b.borrowings = 0
            AND b.year = (
                SELECT MAX(year) FROM balancesheet b2
                WHERE b2.company_id = b.company_id
            )
            ORDER BY b.company_id
        """)
        rows = cursor.fetchall()
        log(f"  Found {len(rows)} debt-free companies:")
        for row in rows:
            log(
                f"  ✅ {row['company_id']:<15} "
                f"{row['broad_sector']}"
            )

        # ── Query 7: CFO health ───────────────────────────────────────
        log("\n💵 QUERY 7: Cash Flow Health Summary")
        log("-" * 40)
        cursor.execute("""
            SELECT
                SUM(CASE WHEN operating_activity > 0 THEN 1 ELSE 0 END) AS positive_cfo,
                SUM(CASE WHEN operating_activity < 0 THEN 1 ELSE 0 END) AS negative_cfo,
                SUM(CASE WHEN operating_activity IS NULL THEN 1 ELSE 0 END) AS null_cfo,
                ROUND(AVG(operating_activity), 0) AS avg_cfo
            FROM cashflow
            WHERE year = (
                SELECT MAX(year) FROM cashflow cf2
                WHERE cf2.company_id = cashflow.company_id
            )
        """)
        row = cursor.fetchone()
        log(f"  Companies with positive CFO: {row['positive_cfo']} ✅")
        log(f"  Companies with negative CFO: {row['negative_cfo']} ⚠️")
        log(f"  Companies with null CFO:     {row['null_cfo']}")
        log(f"  Average CFO across all:      {row['avg_cfo']:,.0f} Cr")

        # ── Query 8: Balance sheet balance ────────────────────────────
        log("\n⚖️  QUERY 8: Balance Sheet Balance Check")
        log("-" * 40)
        cursor.execute("""
            SELECT
                COUNT(*) AS total_rows,
                SUM(CASE WHEN ABS(total_assets - total_liabilities)
                    / NULLIF(total_assets, 0) < 0.01
                    THEN 1 ELSE 0 END) AS balanced_rows,
                SUM(CASE WHEN ABS(total_assets - total_liabilities)
                    / NULLIF(total_assets, 0) >= 0.01
                    THEN 1 ELSE 0 END) AS unbalanced_rows
            FROM balancesheet
            WHERE total_assets > 0
        """)
        row = cursor.fetchone()
        pct = (row["balanced_rows"] / row["total_rows"]) * 100
        log(f"  Total BS rows:     {row['total_rows']}")
        log(f"  Balanced rows:     {row['balanced_rows']} ({pct:.1f}%) ✅")
        log(f"  Unbalanced rows:   {row['unbalanced_rows']} (>1% diff) ⚠️")

        # ── Query 9: Document coverage ────────────────────────────────
        log("\n📄 QUERY 9: Annual Report Coverage")
        log("-" * 40)
        cursor.execute("""
            SELECT
                COUNT(DISTINCT company_id) AS companies_with_reports,
                COUNT(*)                   AS total_reports,
                MIN(year)                  AS earliest_year,
                MAX(year)                  AS latest_year
            FROM documents
        """)
        row = cursor.fetchone()
        log(f"  Companies with reports: {row['companies_with_reports']}")
        log(f"  Total report links:     {row['total_reports']}")
        log(f"  Year range:             {row['earliest_year']} → {row['latest_year']}")

        # ── Query 10: Completeness summary ────────────────────────────
        log("\n✅ QUERY 10: Data Completeness Summary")
        log("-" * 40)
        checks = [
            ("Total companies",              "SELECT COUNT(*) FROM companies"),
            ("With P&L data",               "SELECT COUNT(DISTINCT company_id) FROM profitandloss"),
            ("With BS data",                "SELECT COUNT(DISTINCT company_id) FROM balancesheet"),
            ("With CF data",                "SELECT COUNT(DISTINCT company_id) FROM cashflow"),
            ("With sector mapping",         "SELECT COUNT(DISTINCT company_id) FROM sectors"),
            ("With stock prices",           "SELECT COUNT(DISTINCT company_id) FROM stock_prices"),
            ("With market cap data",        "SELECT COUNT(DISTINCT company_id) FROM market_cap"),
        ]
        for label, query in checks:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            pct   = (count / 92) * 100
            icon  = "✅" if count >= 88 else "⚠️ "
            log(f"  {icon} {label:<30} {count:>3} / 92 ({pct:.0f}%)")

    return lines


def check_sprint1_exit_criteria():
    """
    Check all Sprint 1 exit criteria from the project document.
    Returns True if all pass.
    """
    lines  = []
    passed = 0
    total  = 0

    def log(text=""):
        lines.append(text)
        print(text)

    def check(label, result, expected, comparison="eq"):
        nonlocal passed, total
        total += 1
        if comparison == "eq":
            ok = result == expected
        elif comparison == "ge":
            ok = result >= expected
        elif comparison == "le":
            ok = result <= expected
        elif comparison == "gt":
            ok = result > expected

        icon = "✅ PASS" if ok else "❌ FAIL"
        log(f"  {icon}  {label}")
        log(f"         Expected: {expected}  Got: {result}")
        if ok:
            passed += 1
        return ok

    log("\n" + "=" * 65)
    log("SPRINT 1 EXIT CRITERIA CHECK")
    log("=" * 65)

    with get_conn() as conn:
        cursor = conn.cursor()

        # AC-01: 92 companies
        cursor.execute("SELECT COUNT(*) FROM companies")
        check("AC-01: Company count = 92",
              cursor.fetchone()[0], 92)

        # AC-02: >= 80% companies have 10yr data
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT company_id
                FROM profitandloss
                GROUP BY company_id
                HAVING COUNT(DISTINCT year) >= 10
            )
        """)
        count_10yr = cursor.fetchone()[0]
        pct_10yr   = (count_10yr / 92) * 100
        check("AC-02: >= 80% companies have 10yr P&L data",
              round(pct_10yr, 0), 80, "ge")

        # AC-03: 0 orphan rows
        cursor.execute("""
            SELECT COUNT(*) FROM profitandloss
            WHERE company_id NOT IN (SELECT id FROM companies)
        """)
        check("AC-03: P&L orphan rows = 0",
              cursor.fetchone()[0], 0)

        cursor.execute("""
            SELECT COUNT(*) FROM balancesheet
            WHERE company_id NOT IN (SELECT id FROM companies)
        """)
        check("AC-03: BS orphan rows = 0",
              cursor.fetchone()[0], 0)

        cursor.execute("""
            SELECT COUNT(*) FROM cashflow
            WHERE company_id NOT IN (SELECT id FROM companies)
        """)
        check("AC-03: CF orphan rows = 0",
              cursor.fetchone()[0], 0)

        # AC-04: financial_ratios not needed yet (Sprint 2)
        # Just check profitandloss has > 1000 rows
        cursor.execute("SELECT COUNT(*) FROM profitandloss")
        check("P&L rows >= 1000",
              cursor.fetchone()[0], 1000, "ge")

        # Sectors: all 92 companies mapped
        cursor.execute("SELECT COUNT(*) FROM sectors")
        check("All 92 companies have sector mapping",
              cursor.fetchone()[0], 92)

        # Stock prices loaded
        cursor.execute("SELECT COUNT(*) FROM stock_prices")
        check("Stock prices rows >= 5000",
              cursor.fetchone()[0], 5000, "ge")

        # Documents loaded
        cursor.execute("SELECT COUNT(*) FROM documents")
        check("Documents rows >= 1000",
              cursor.fetchone()[0], 1000, "ge")

    log(f"\n  Results: {passed}/{total} criteria passed")

    if passed == total:
        log("\n  🎉 ALL EXIT CRITERIA PASSED!")
        log("  ✅ Sprint 1 is COMPLETE")
        log("  ✅ Ready to start Sprint 2 — Financial Ratio Engine")
    else:
        log(f"\n  ⚠️  {total - passed} criteria failed — review before proceeding")

    return lines, passed == total


def save_sprint_summary(query_lines, criteria_lines, all_passed):
    """Save complete sprint summary to file."""
    output_file = OUTPUT_PATH / "sprint1_summary.txt"

    all_lines = []
    all_lines.append("=" * 65)
    all_lines.append("NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM")
    all_lines.append("SPRINT 1 — DATA FOUNDATION — COMPLETE SUMMARY")
    all_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    all_lines.append("=" * 65)
    all_lines.append("")
    all_lines.extend(query_lines)
    all_lines.append("")
    all_lines.extend(criteria_lines)
    all_lines.append("")
    all_lines.append("=" * 65)
    all_lines.append("SPRINT 1 DELIVERABLES")
    all_lines.append("=" * 65)
    deliverables = [
        ("D-01", "nifty100.db",                  "✅ Created — 10 tables, 10,999 rows"),
        ("D-02", "load_audit.csv",               "✅ Generated — all 12 files logged"),
        ("D-03", "validation_failures.csv",      "✅ Generated — 0 CRITICAL, 319 WARNING"),
        ("D-04", "exploratory_queries.sql",      "✅ Created — 10 queries"),
        ("D-05", "src/etl/loader.py",            "✅ Created — loads all 12 files"),
        ("D-06", "src/etl/normaliser.py",        "✅ Created — normalize_year/ticker"),
        ("D-07", "src/etl/validator.py",         "✅ Created — 16 DQ rules"),
        ("D-08", "src/etl/db_setup.py",          "✅ Created — schema setup"),
        ("D-09", "src/etl/review.py",            "✅ Created — manual review"),
        ("D-10", "db/schema.sql",                "✅ Created — 10 table definitions"),
        ("D-11", "tests/etl/test_normalise.py",  "✅ Created — 40+ tests"),
        ("D-12", "tests/dq/test_rules.py",       "✅ Created — DQ rule tests"),
    ]
    for d_id, name, status in deliverables:
        all_lines.append(f"  {d_id}  {name:<35} {status}")

    all_lines.append("")
    all_lines.append("=" * 65)
    if all_passed:
        all_lines.append("🎉 SPRINT 1 SIGNED OFF — READY FOR SPRINT 2")
    else:
        all_lines.append("⚠️  SPRINT 1 NEEDS REVIEW BEFORE SIGN-OFF")
    all_lines.append("=" * 65)

    output_file.write_text("\n".join(all_lines), encoding="utf-8")
    logger.info("Sprint summary saved to: %s", output_file)
    return output_file


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🚀 Running Sprint 1 Final Verification...\n")

    # Run exploratory queries
    query_lines = run_exploratory_queries()

    # Check exit criteria
    criteria_lines, all_passed = check_sprint1_exit_criteria()

    # Save summary
    output_file = save_sprint_summary(
        query_lines, criteria_lines, all_passed
    )

    print(f"\n📄 Sprint summary saved to: {output_file}")
    print("\n" + "=" * 65)

    if all_passed:
        print("🎉 SPRINT 1 COMPLETE!")
        print("✅ All exit criteria passed")
        print("✅ Ready for Sprint 2 — Financial Ratio Engine")
    else:
        print("⚠️  Some criteria failed — review sprint1_summary.txt")

    print("=" * 65)