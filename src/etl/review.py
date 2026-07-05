"""
review.py — Manual Data Quality Review Script

Picks 5 random companies and checks their data
across all tables. Saves findings to output/manual_review.txt

Run with:
    python src/etl/review.py

Author: Samadhan
Sprint: 1 — Day 6
"""

import sqlite3
import random
import logging
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import DB_PATH, OUTPUT_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# REVIEW CHECKS
# ─────────────────────────────────────────────────────────────────────────────

def get_connection():
    """Get SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def check_overall_counts(conn) -> dict:
    """
    Check row counts for all 10 tables.
    Returns dict of table → count.
    """
    tables = [
        "companies", "profitandloss", "balancesheet",
        "cashflow", "analysis", "documents", "prosandcons",
        "sectors", "stock_prices", "market_cap"
    ]
    counts = {}
    cursor = conn.cursor()
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]
    return counts


def get_random_companies(conn, n: int = 5) -> list:
    """Pick n random companies from the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, company_name FROM companies ORDER BY RANDOM() LIMIT ?", (n,))
    return cursor.fetchall()


def check_company_pl(conn, company_id: str) -> dict:
    """Check P&L data for one company."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT year, sales, net_profit, eps, opm_percentage
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY year DESC
        LIMIT 5
    """, (company_id,))
    return cursor.fetchall()


def check_company_bs(conn, company_id: str) -> dict:
    """Check Balance Sheet data for one company."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT year, total_assets, total_liabilities,
               borrowings, reserves
        FROM balancesheet
        WHERE company_id = ?
        ORDER BY year DESC
        LIMIT 5
    """, (company_id,))
    return cursor.fetchall()


def check_company_cf(conn, company_id: str) -> dict:
    """Check Cash Flow data for one company."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT year, operating_activity,
               investing_activity, financing_activity
        FROM cashflow
        WHERE company_id = ?
        ORDER BY year DESC
        LIMIT 5
    """, (company_id,))
    return cursor.fetchall()


def check_company_sector(conn, company_id: str):
    """Check sector data for one company."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT broad_sector, sub_sector, market_cap_category
        FROM sectors
        WHERE company_id = ?
    """, (company_id,))
    return cursor.fetchone()


def check_year_coverage(conn) -> dict:
    """
    Check how many years of data each company has.
    Flag companies with less than 5 years.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT company_id,
               COUNT(DISTINCT year) as year_count,
               MIN(year) as earliest,
               MAX(year) as latest
        FROM profitandloss
        GROUP BY company_id
        ORDER BY year_count ASC
        LIMIT 10
    """)
    return cursor.fetchall()


def check_null_counts(conn) -> dict:
    """Check for NULL values in critical columns."""
    cursor = conn.cursor()
    checks = {
        "pl_sales_null":      "SELECT COUNT(*) FROM profitandloss WHERE sales IS NULL",
        "pl_profit_null":     "SELECT COUNT(*) FROM profitandloss WHERE net_profit IS NULL",
        "bs_assets_null":     "SELECT COUNT(*) FROM balancesheet WHERE total_assets IS NULL",
        "cf_cfo_null":        "SELECT COUNT(*) FROM cashflow WHERE operating_activity IS NULL",
        "companies_name_null":"SELECT COUNT(*) FROM companies WHERE company_name IS NULL",
    }
    results = {}
    for key, query in checks.items():
        cursor.execute(query)
        results[key] = cursor.fetchone()[0]
    return results


def check_top_companies(conn) -> list:
    """Get top 5 companies by latest sales."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.company_id, c.company_name,
               p.year, p.sales, p.net_profit
        FROM profitandloss p
        JOIN companies c ON p.company_id = c.id
        WHERE p.year = (
            SELECT MAX(year) FROM profitandloss p2
            WHERE p2.company_id = p.company_id
        )
        ORDER BY p.sales DESC
        LIMIT 5
    """)
    return cursor.fetchall()


def check_companies_with_no_debt(conn) -> list:
    """Find debt-free companies (borrowings = 0)."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.company_id, c.company_name, b.year, b.borrowings
        FROM balancesheet b
        JOIN companies c ON b.company_id = c.id
        WHERE b.borrowings = 0
        AND b.year = (
            SELECT MAX(year) FROM balancesheet b2
            WHERE b2.company_id = b.company_id
        )
        ORDER BY b.company_id
        LIMIT 10
    """)
    return cursor.fetchall()


def check_acceptance_criteria(conn) -> dict:
    """
    Check Sprint 1 exit criteria from the project document.
    """
    cursor = conn.cursor()
    results = {}

    # AC-01: 92 companies
    cursor.execute("SELECT COUNT(*) FROM companies")
    results["AC01_company_count"] = cursor.fetchone()[0]

    # AC-02: Companies with >= 10 years of P&L
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT company_id, COUNT(DISTINCT year) as yr_count
            FROM profitandloss
            GROUP BY company_id
            HAVING yr_count >= 10
        )
    """)
    results["AC02_companies_with_10yr"] = cursor.fetchone()[0]

    # AC-03: No FK violations (manual check)
    cursor.execute("""
        SELECT COUNT(*) FROM profitandloss
        WHERE company_id NOT IN (SELECT id FROM companies)
    """)
    results["AC03_pl_orphans"] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM balancesheet
        WHERE company_id NOT IN (SELECT id FROM companies)
    """)
    results["AC03_bs_orphans"] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM cashflow
        WHERE company_id NOT IN (SELECT id FROM companies)
    """)
    results["AC03_cf_orphans"] = cursor.fetchone()[0]

    return results


# ─────────────────────────────────────────────────────────────────────────────
# MAIN REVIEW RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_review():
    """Run the complete manual review and save to file."""

    output_file = OUTPUT_PATH / "manual_review.txt"
    lines       = []

    def log(text=""):
        """Add line to output and print it."""
        lines.append(text)
        print(text)

    log("=" * 60)
    log("NIFTY 100 — SPRINT 1 MANUAL REVIEW")
    log(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    with get_connection() as conn:

        # ── Section 1: Overall Counts ─────────────────────────────────────
        log("\n📊 SECTION 1: TABLE ROW COUNTS")
        log("-" * 40)
        counts = check_overall_counts(conn)
        total  = 0
        for table, count in counts.items():
            status = "✅" if count > 0 else "❌"
            log(f"  {status} {table:<25} {count:>6} rows")
            total += count
        log(f"\n  Total rows in database: {total:,}")

        # ── Section 2: Acceptance Criteria ───────────────────────────────
        log("\n📋 SECTION 2: SPRINT 1 ACCEPTANCE CRITERIA")
        log("-" * 40)
        ac = check_acceptance_criteria(conn)

        company_count = ac["AC01_company_count"]
        log(f"  AC-01 Company count = {company_count} "
            f"{'✅' if company_count == 92 else '❌'} (expected 92)")

        yr10_count = ac["AC02_companies_with_10yr"]
        pct = (yr10_count / 92) * 100
        log(f"  AC-02 Companies with 10yr data = {yr10_count} "
            f"({pct:.0f}%) {'✅' if pct >= 80 else '⚠️'}")

        pl_orphans = ac["AC03_pl_orphans"]
        bs_orphans = ac["AC03_bs_orphans"]
        cf_orphans = ac["AC03_cf_orphans"]
        log(f"  AC-03 Orphan rows:")
        log(f"        P&L orphans     = {pl_orphans} {'✅' if pl_orphans == 0 else '❌'}")
        log(f"        BS orphans      = {bs_orphans} {'✅' if bs_orphans == 0 else '❌'}")
        log(f"        CF orphans      = {cf_orphans} {'✅' if cf_orphans == 0 else '❌'}")

        # ── Section 3: NULL Value Check ───────────────────────────────────
        log("\n🔍 SECTION 3: NULL VALUE CHECK")
        log("-" * 40)
        nulls = check_null_counts(conn)
        for col, count in nulls.items():
            status = "✅" if count == 0 else "⚠️ "
            log(f"  {status} {col:<30} {count} nulls")

        # ── Section 4: Top Companies by Sales ────────────────────────────
        log("\n🏆 SECTION 4: TOP 5 COMPANIES BY LATEST SALES")
        log("-" * 40)
        top = check_top_companies(conn)
        for row in top:
            log(
                f"  {row['company_id']:<15} "
                f"{str(row['company_name'])[:25]:<25} "
                f"Sales: {row['sales']:>10,.0f} Cr  "
                f"Profit: {row['net_profit']:>8,.0f} Cr"
            )

        # ── Section 5: Debt-Free Companies ───────────────────────────────
        log("\n💰 SECTION 5: DEBT-FREE COMPANIES (latest year)")
        log("-" * 40)
        debt_free = check_companies_with_no_debt(conn)
        log(f"  Found {len(debt_free)} debt-free companies:")
        for row in debt_free:
            log(f"  ✅ {row['company_id']:<15} {str(row['company_name'])[:30]}")

        # ── Section 6: Year Coverage ──────────────────────────────────────
        log("\n📅 SECTION 6: COMPANIES WITH LEAST DATA (bottom 10)")
        log("-" * 40)
        coverage = check_year_coverage(conn)
        for row in coverage:
            status = "⚠️ " if row["year_count"] < 5 else "✅"
            log(
                f"  {status} {row['company_id']:<15} "
                f"{row['year_count']:>2} years  "
                f"({row['earliest']} → {row['latest']})"
            )

        # ── Section 7: 5 Random Company Deep Dive ────────────────────────
        log("\n🔎 SECTION 7: RANDOM COMPANY DEEP DIVE (5 companies)")
        log("-" * 40)

        companies = get_random_companies(conn, 5)
        for company in companies:
            cid  = company["id"]
            name = company["company_name"]

            log(f"\n  ── {cid} — {name}")

            # Sector
            sector = check_company_sector(conn, cid)
            if sector:
                log(f"     Sector: {sector['broad_sector']} → {sector['sub_sector']}")
            else:
                log(f"     Sector: ⚠️  Not found in sectors table")

            # P&L (latest 3 years)
            pl_rows = check_company_pl(conn, cid)
            if pl_rows:
                log(f"     P&L (latest years):")
                for row in pl_rows[:3]:
                    sales  = row["sales"]  or 0
                    profit = row["net_profit"] or 0
                    opm    = row["opm_percentage"] or 0
                    log(
                        f"       {row['year']}  "
                        f"Sales: {sales:>10,.0f}  "
                        f"Profit: {profit:>8,.0f}  "
                        f"OPM: {opm:.1f}%"
                    )
            else:
                log(f"     P&L: ⚠️  No data found")

            # Balance Sheet (latest year)
            bs_rows = check_company_bs(conn, cid)
            if bs_rows:
                row    = bs_rows[0]
                assets = row["total_assets"] or 0
                debt   = row["borrowings"]   or 0
                log(
                    f"     BS ({row['year']}):  "
                    f"Assets: {assets:>10,.0f}  "
                    f"Debt: {debt:>8,.0f}"
                )
            else:
                log(f"     BS: ⚠️  No data found")

            # Cash Flow (latest year)
            cf_rows = check_company_cf(conn, cid)
            if cf_rows:
                row = cf_rows[0]
                cfo = row["operating_activity"] or 0
                cfi = row["investing_activity"] or 0
                log(
                    f"     CF ({row['year']}):  "
                    f"CFO: {cfo:>8,.0f}  "
                    f"CFI: {cfi:>8,.0f}"
                )
            else:
                log(f"     CF: ⚠️  No data found")

        # ── Summary ───────────────────────────────────────────────────────
        log("\n" + "=" * 60)
        log("REVIEW SUMMARY")
        log("=" * 60)
        log(f"  Total rows in DB:      {total:,}")
        log(f"  Companies:             {company_count}")
        log(f"  Companies with 10yr:   {yr10_count} ({pct:.0f}%)")
        log(f"  Orphan rows (P&L/BS/CF): {pl_orphans + bs_orphans + cf_orphans}")
        log(f"  Debt-free companies:   {len(debt_free)}")
        log()
        if pl_orphans == 0 and bs_orphans == 0 and cf_orphans == 0:
            log("  ✅ Data quality is ACCEPTABLE for Sprint 1")
            log("  ✅ Ready to proceed to Sprint 2 — Ratio Engine")
        else:
            log("  ⚠️  Some issues found — review before proceeding")
        log("=" * 60)

    # Save to file
    output_file.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Review saved to: %s", output_file)
    print(f"\n📄 Full review saved to: {output_file}")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_review()