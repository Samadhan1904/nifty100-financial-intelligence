"""
loader.py — Main ETL Pipeline for Nifty 100 Financial Intelligence Platform.

Reads all 12 Excel files, cleans data, validates, and loads into SQLite.

Steps:
1. Read Excel files into pandas DataFrames
2. Normalize year and ticker columns
3. Filter orphan rows (company_id not in companies)
4. Load into SQLite database in chunks
5. Generate load_audit.csv

Run with:
    python src/etl/loader.py
    OR
    make load

Author: Samadhan
Sprint: 1 — Day 5
"""

import sqlite3
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import (
    DB_PATH,
    OUTPUT_PATH,
    COMPANIES_FILE,
    PROFITLOSS_FILE,
    BALANCESHEET_FILE,
    CASHFLOW_FILE,
    ANALYSIS_FILE,
    DOCUMENTS_FILE,
    PROSCONS_FILE,
    SECTORS_FILE,
    STOCK_PRICES_FILE,
    MARKET_CAP_FILE,
)
from src.etl.normaliser import normalize_year_series, normalize_ticker_series
from src.etl.validator import validate_dataframes
from src.etl.db_setup import create_database

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────────────────────────────────────────

audit_log = []


def log_audit(
    table: str,
    file: str,
    rows_in: int,
    rows_out: int,
    rejected: int,
    status: str,
    notes: str = "",
    runtime_s: float = 0.0,
):
    """Add one entry to the audit log."""
    audit_log.append({
        "table":     table,
        "file":      file,
        "rows_in":   rows_in,
        "rows_out":  rows_out,
        "rejected":  rejected,
        "status":    status,
        "notes":     notes,
        "runtime_s": round(runtime_s, 2),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


def save_audit():
    """Save audit log to output/load_audit.csv"""
    audit_file = OUTPUT_PATH / "load_audit.csv"
    df = pd.DataFrame(audit_log)
    df.to_csv(audit_file, index=False)
    logger.info("Audit log saved to: %s", audit_file)
    return audit_file


# ─────────────────────────────────────────────────────────────────────────────
# EXCEL READER
# ─────────────────────────────────────────────────────────────────────────────

def read_excel(
    filepath: Path,
    header_row: int = 0,
    table_name: str = "",
) -> Optional[pd.DataFrame]:
    """
    Safely read an Excel file into a DataFrame.

    Args:
        filepath:   Path to Excel file
        header_row: 0 for supplementary files, 1 for core files
        table_name: Name for logging

    Returns:
        DataFrame or None if error
    """
    if not filepath.exists():
        logger.error("File not found: %s", filepath)
        log_audit(
            table=table_name,
            file=filepath.name,
            rows_in=0,
            rows_out=0,
            rejected=0,
            status="ERROR",
            notes=f"File not found: {filepath}",
        )
        return None

    try:
        start = datetime.now()
        df    = pd.read_excel(filepath, header=header_row)
        elapsed = (datetime.now() - start).total_seconds()
        logger.info(
            "Read %s: %d rows, %d cols in %.2fs",
            filepath.name, len(df), len(df.columns), elapsed
        )
        return df

    except Exception as e:
        logger.error("Failed to read %s: %s", filepath.name, e)
        log_audit(
            table=table_name,
            file=filepath.name,
            rows_in=0,
            rows_out=0,
            rejected=0,
            status="ERROR",
            notes=str(e),
        )
        return None


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE LOADER — chunked insert to avoid "too many SQL variables"
# ─────────────────────────────────────────────────────────────────────────────

def load_table(
    df: pd.DataFrame,
    table_name: str,
    file_name: str,
    if_exists: str = "append",
) -> int:
    """
    Load DataFrame into SQLite table using chunked inserts.

    Args:
        df:         DataFrame to load
        table_name: Target SQLite table
        file_name:  Source filename for audit
        if_exists:  append or replace

    Returns:
        Number of rows in table after load
    """
    start   = datetime.now()
    rows_in = len(df)

    if rows_in == 0:
        logger.warning("Skipping %s — empty DataFrame", table_name)
        log_audit(
            table=table_name,
            file=file_name,
            rows_in=0,
            rows_out=0,
            rejected=0,
            status="SKIPPED",
            notes="Empty DataFrame",
        )
        return 0

    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Disable FK during load for speed
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")

            # Chunked insert — avoids "too many SQL variables" error
            chunk_size = 200
            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i:i + chunk_size]
                chunk.to_sql(
                    name=table_name,
                    con=conn,
                    if_exists="append" if i > 0 else if_exists,
                    index=False,
                )

            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()

            # Get final row count
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            rows_out = cursor.fetchone()[0]

        elapsed  = (datetime.now() - start).total_seconds()
        rejected = max(0, rows_in - rows_out)

        logger.info(
            "Loaded %-20s %d → %d rows (rejected: %d) in %.2fs",
            table_name, rows_in, rows_out, rejected, elapsed
        )

        log_audit(
            table=table_name,
            file=file_name,
            rows_in=rows_in,
            rows_out=rows_out,
            rejected=rejected,
            status="OK" if rejected == 0 else "PARTIAL",
            runtime_s=elapsed,
        )
        return rows_out

    except Exception as e:
        elapsed = (datetime.now() - start).total_seconds()
        logger.error("Failed to load %s: %s", table_name, e)
        log_audit(
            table=table_name,
            file=file_name,
            rows_in=rows_in,
            rows_out=0,
            rejected=rows_in,
            status="ERROR",
            notes=str(e),
            runtime_s=elapsed,
        )
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — filter orphan rows
# ─────────────────────────────────────────────────────────────────────────────

def filter_valid_ids(
    df: pd.DataFrame,
    valid_ids: set,
    table_name: str,
    id_col: str = "company_id",
) -> pd.DataFrame:
    """
    Remove rows where company_id is not in the companies table.

    Args:
        df:         DataFrame to filter
        valid_ids:  Set of valid NSE tickers from companies table
        table_name: Name for logging
        id_col:     Column name containing company ID

    Returns:
        Filtered DataFrame
    """
    if not valid_ids or id_col not in df.columns:
        return df

    before = len(df)
    df     = df[df[id_col].isin(valid_ids)]
    after  = len(df)

    if before != after:
        logger.warning(
            "%s: removed %d orphan rows (company_id not in companies)",
            table_name, before - after
        )

    return df


# ─────────────────────────────────────────────────────────────────────────────
# INDIVIDUAL TABLE LOADERS
# ─────────────────────────────────────────────────────────────────────────────

def load_companies() -> Optional[pd.DataFrame]:
    """Load companies.xlsx → companies table"""
    logger.info("── Loading companies ──────────────────")

    df = read_excel(COMPANIES_FILE, header_row=1, table_name="companies")
    if df is None:
        return None

    # Clean column names
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("(", "")
        .str.replace(")", "")
    )

    # First column is always the ticker/id
    first_col = df.columns[0]
    if first_col != "id":
        df = df.rename(columns={first_col: "id"})

    # Normalize ticker
    df["id"] = normalize_ticker_series(df["id"])

    # Remove empty IDs
    before = len(df)
    df = df[df["id"].str.len() >= 2]
    after  = len(df)
    if before != after:
        logger.warning(
            "companies: removed %d rows with invalid id", before - after
        )

    # Remove duplicates
    df = df.drop_duplicates(subset=["id"], keep="first")

    # Select only schema columns that exist
    schema_cols = [
        "id", "company_logo", "company_name", "chart_link",
        "about_company", "website", "nse_profile", "bse_profile",
        "face_value", "book_value", "roce_percentage", "roe_percentage"
    ]
    existing = [c for c in schema_cols if c in df.columns]
    df = df[existing]

    load_table(df, "companies", COMPANIES_FILE.name, if_exists="replace")
    logger.info("Companies loaded: %d", len(df))
    return df


def load_profitandloss(valid_ids: set = None) -> Optional[pd.DataFrame]:
    """Load profitandloss.xlsx → profitandloss table"""
    logger.info("── Loading profitandloss ──────────────")

    df = read_excel(PROFITLOSS_FILE, header_row=1, table_name="profitandloss")
    if df is None:
        return None

    # Clean column names
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Find and rename company_id column
    for col in ["company_id", "company", "ticker", "scrip_id"]:
        if col in df.columns:
            df = df.rename(columns={col: "company_id"})
            break

    # Normalize
    df["company_id"] = normalize_ticker_series(df["company_id"])
    df["year"]       = normalize_year_series(df["year"])

    # Remove PARSE_ERROR years (TTM, partial years etc.)
    before = len(df)
    df = df[df["year"] != "PARSE_ERROR"]
    after  = len(df)
    if before != after:
        logger.warning(
            "profitandloss: removed %d rows with unparseable year "
            "(TTM, partial etc.)",
            before - after
        )

    # Filter orphan company IDs
    df = filter_valid_ids(df, valid_ids, "profitandloss")

    # Remove duplicates
    df = df.drop_duplicates(subset=["company_id", "year"], keep="last")

    # Drop auto-increment id
    if "id" in df.columns:
        df = df.drop(columns=["id"])

    # Select schema columns
    schema_cols = [
        "company_id", "year", "sales", "expenses", "operating_profit",
        "opm_percentage", "other_income", "interest", "depreciation",
        "profit_before_tax", "tax_percentage", "net_profit",
        "eps", "dividend_payout"
    ]
    existing = [c for c in schema_cols if c in df.columns]
    df = df[existing]

    load_table(df, "profitandloss", PROFITLOSS_FILE.name)
    return df


def load_balancesheet(valid_ids: set = None) -> Optional[pd.DataFrame]:
    """Load balancesheet.xlsx → balancesheet table"""
    logger.info("── Loading balancesheet ───────────────")

    df = read_excel(BALANCESHEET_FILE, header_row=1, table_name="balancesheet")
    if df is None:
        return None

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    for col in ["company_id", "company", "ticker", "scrip_id"]:
        if col in df.columns:
            df = df.rename(columns={col: "company_id"})
            break

    df["company_id"] = normalize_ticker_series(df["company_id"])
    df["year"]       = normalize_year_series(df["year"])

    before = len(df)
    df = df[df["year"] != "PARSE_ERROR"]
    after  = len(df)
    if before != after:
        logger.warning(
            "balancesheet: removed %d rows with unparseable year",
            before - after
        )

    df = filter_valid_ids(df, valid_ids, "balancesheet")
    df = df.drop_duplicates(subset=["company_id", "year"], keep="last")

    if "id" in df.columns:
        df = df.drop(columns=["id"])

    schema_cols = [
        "company_id", "year", "equity_capital", "reserves",
        "borrowings", "other_liabilities", "total_liabilities",
        "fixed_assets", "cwip", "investments", "other_asset", "total_assets"
    ]
    existing = [c for c in schema_cols if c in df.columns]
    df = df[existing]

    load_table(df, "balancesheet", BALANCESHEET_FILE.name)
    return df


def load_cashflow(valid_ids: set = None) -> Optional[pd.DataFrame]:
    """Load cashflow.xlsx → cashflow table"""
    logger.info("── Loading cashflow ───────────────────")

    df = read_excel(CASHFLOW_FILE, header_row=1, table_name="cashflow")
    if df is None:
        return None

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    for col in ["company_id", "company", "ticker", "scrip_id"]:
        if col in df.columns:
            df = df.rename(columns={col: "company_id"})
            break

    df["company_id"] = normalize_ticker_series(df["company_id"])
    df["year"]       = normalize_year_series(df["year"])

    before = len(df)
    df = df[df["year"] != "PARSE_ERROR"]
    after  = len(df)
    if before != after:
        logger.warning(
            "cashflow: removed %d rows with unparseable year",
            before - after
        )

    df = filter_valid_ids(df, valid_ids, "cashflow")
    df = df.drop_duplicates(subset=["company_id", "year"], keep="last")

    if "id" in df.columns:
        df = df.drop(columns=["id"])

    schema_cols = [
        "company_id", "year",
        "operating_activity", "investing_activity",
        "financing_activity", "net_cash_flow"
    ]
    existing = [c for c in schema_cols if c in df.columns]
    df = df[existing]

    load_table(df, "cashflow", CASHFLOW_FILE.name)
    return df


def load_analysis(valid_ids: set = None) -> Optional[pd.DataFrame]:
    """Load analysis.xlsx → analysis table"""
    logger.info("── Loading analysis ───────────────────")

    df = read_excel(ANALYSIS_FILE, header_row=1, table_name="analysis")
    if df is None:
        return None

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    for col in ["company_id", "company", "ticker", "scrip_id"]:
        if col in df.columns:
            df = df.rename(columns={col: "company_id"})
            break

    df["company_id"] = normalize_ticker_series(df["company_id"])
    df = filter_valid_ids(df, valid_ids, "analysis")
    df = df.drop_duplicates(subset=["company_id"], keep="first")

    if "id" in df.columns:
        df = df.drop(columns=["id"])

    schema_cols = [
        "company_id", "compounded_sales_growth",
        "compounded_profit_growth", "stock_price_cagr", "roe"
    ]
    existing = [c for c in schema_cols if c in df.columns]
    df = df[existing]

    load_table(df, "analysis", ANALYSIS_FILE.name)
    return df


def load_documents(valid_ids: set = None) -> Optional[pd.DataFrame]:
    """Load documents.xlsx → documents table"""
    logger.info("── Loading documents ──────────────────")

    df = read_excel(DOCUMENTS_FILE, header_row=1, table_name="documents")
    if df is None:
        return None

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    for col in ["company_id", "company", "ticker", "scrip_id"]:
        if col in df.columns:
            df = df.rename(columns={col: "company_id"})
            break

    df["company_id"] = normalize_ticker_series(df["company_id"])

    # Rename annual report column
    for col in ["annual_report", "annual_report_link", "report_link", "link"]:
        if col in df.columns:
            df = df.rename(columns={col: "annual_report"})
            break

    # Rename year column — documents uses capital Y
    for col in ["year", "Year", "YEAR"]:
        if col in df.columns:
            df = df.rename(columns={col: "year"})
            break

    df = filter_valid_ids(df, valid_ids, "documents")
    df = df.drop_duplicates(subset=["company_id", "year"], keep="first")

    if "id" in df.columns:
        df = df.drop(columns=["id"])

    schema_cols = ["company_id", "year", "annual_report"]
    existing = [c for c in schema_cols if c in df.columns]
    df = df[existing]

    load_table(df, "documents", DOCUMENTS_FILE.name)
    return df


def load_prosandcons(valid_ids: set = None) -> Optional[pd.DataFrame]:
    """Load prosandcons.xlsx → prosandcons table"""
    logger.info("── Loading prosandcons ────────────────")

    df = read_excel(PROSCONS_FILE, header_row=1, table_name="prosandcons")
    if df is None:
        return None

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    for col in ["company_id", "company", "ticker", "scrip_id"]:
        if col in df.columns:
            df = df.rename(columns={col: "company_id"})
            break

    df["company_id"] = normalize_ticker_series(df["company_id"])
    df = filter_valid_ids(df, valid_ids, "prosandcons")

    if "id" in df.columns:
        df = df.drop(columns=["id"])

    schema_cols = ["company_id", "pros", "cons"]
    existing = [c for c in schema_cols if c in df.columns]
    df = df[existing]

    load_table(df, "prosandcons", PROSCONS_FILE.name)
    return df


def load_sectors(valid_ids: set = None) -> Optional[pd.DataFrame]:
    """Load sectors.xlsx → sectors table"""
    logger.info("── Loading sectors ────────────────────")

    df = read_excel(SECTORS_FILE, header_row=0, table_name="sectors")
    if df is None:
        return None

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    for col in ["company_id", "company", "ticker", "scrip_id"]:
        if col in df.columns:
            df = df.rename(columns={col: "company_id"})
            break

    df["company_id"] = normalize_ticker_series(df["company_id"])
    df = filter_valid_ids(df, valid_ids, "sectors")
    df = df.drop_duplicates(subset=["company_id"], keep="first")

    if "id" in df.columns:
        df = df.drop(columns=["id"])

    schema_cols = [
        "company_id", "broad_sector", "sub_sector",
        "index_weight_pct", "market_cap_category"
    ]
    existing = [c for c in schema_cols if c in df.columns]
    df = df[existing]

    load_table(df, "sectors", SECTORS_FILE.name)
    return df


def load_stock_prices(valid_ids: set = None) -> Optional[pd.DataFrame]:
    """Load stock_prices.xlsx → stock_prices table"""
    logger.info("── Loading stock_prices ───────────────")

    df = read_excel(STOCK_PRICES_FILE, header_row=0, table_name="stock_prices")
    if df is None:
        return None

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    for col in ["company_id", "company", "ticker", "scrip_id"]:
        if col in df.columns:
            df = df.rename(columns={col: "company_id"})
            break

    df["company_id"] = normalize_ticker_series(df["company_id"])
    df = filter_valid_ids(df, valid_ids, "stock_prices")
    df = df.drop_duplicates(subset=["company_id", "date"], keep="first")

    if "id" in df.columns:
        df = df.drop(columns=["id"])

    schema_cols = [
        "company_id", "date", "open_price", "high_price",
        "low_price", "close_price", "volume", "adjusted_close"
    ]
    existing = [c for c in schema_cols if c in df.columns]
    df = df[existing]

    load_table(df, "stock_prices", STOCK_PRICES_FILE.name)
    return df


def load_market_cap(valid_ids: set = None) -> Optional[pd.DataFrame]:
    """Load market_cap.xlsx → market_cap table"""
    logger.info("── Loading market_cap ─────────────────")

    df = read_excel(MARKET_CAP_FILE, header_row=0, table_name="market_cap")
    if df is None:
        return None

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    for col in ["company_id", "company", "ticker", "scrip_id"]:
        if col in df.columns:
            df = df.rename(columns={col: "company_id"})
            break

    df["company_id"] = normalize_ticker_series(df["company_id"])
    df = filter_valid_ids(df, valid_ids, "market_cap")
    df = df.drop_duplicates(subset=["company_id", "year"], keep="first")

    if "id" in df.columns:
        df = df.drop(columns=["id"])

    schema_cols = [
        "company_id", "year", "market_cap_crore",
        "enterprise_value_crore", "pe_ratio", "pb_ratio",
        "ev_ebitda", "dividend_yield_pct"
    ]
    existing = [c for c in schema_cols if c in df.columns]
    df = df[existing]

    load_table(df, "market_cap", MARKET_CAP_FILE.name)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline():
    """
    Run the complete ETL pipeline.

    Load order:
    1. companies  — MUST be first (all other tables FK to it)
    2. Core tables — profitandloss, balancesheet, cashflow
    3. Other core  — analysis, documents, prosandcons
    4. Supplementary — sectors, stock_prices, market_cap
    """
    start_time = datetime.now()

    print("=" * 60)
    print("Nifty 100 — ETL Pipeline")
    print("=" * 60)

    # ── Step 1: Ensure database exists ───────────────────────────────────
    logger.info("Step 1: Setting up database...")
    if not DB_PATH.exists():
        logger.info("Database not found — creating now...")
        create_database()
    else:
        logger.info("Database found: %s", DB_PATH)

    # ── Step 2: Clear existing data ───────────────────────────────────────
    logger.info("Clearing existing data for fresh load...")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            for table in [
                "market_cap", "stock_prices", "sectors",
                "prosandcons", "documents", "analysis",
                "cashflow", "balancesheet", "profitandloss", "companies"
            ]:
                conn.execute(f"DELETE FROM {table}")
            conn.commit()
        logger.info("Existing data cleared")
    except sqlite3.Error as e:
        logger.error("Could not clear data: %s", e)

    # ── Step 3: Load companies FIRST ──────────────────────────────────────
    logger.info("Step 3: Loading all 12 files...")
    companies_df = load_companies()

    # Build set of valid IDs for filtering all other tables
    valid_ids = set()
    if companies_df is not None and not companies_df.empty:
        valid_ids = set(companies_df["id"].dropna().unique())
        logger.info(
            "Valid company IDs: %d tickers loaded", len(valid_ids)
        )
    else:
        logger.error(
            "Companies table failed to load! "
            "All other tables will have no valid IDs to filter against."
        )

    # ── Step 4: Load all remaining tables ────────────────────────────────
    # Core financial tables
    pl_df = load_profitandloss(valid_ids)
    bs_df = load_balancesheet(valid_ids)
    cf_df = load_cashflow(valid_ids)

    # Other core tables
    load_analysis(valid_ids)
    load_documents(valid_ids)
    load_prosandcons(valid_ids)

    # Supplementary tables
    load_sectors(valid_ids)
    load_stock_prices(valid_ids)
    load_market_cap(valid_ids)

    # ── Step 5: Run DQ validation ─────────────────────────────────────────
    logger.info("Step 5: Running data quality validation...")

    dfs = {}
    if companies_df is not None:
        dfs["companies"] = companies_df
    if pl_df is not None:
        dfs["profitandloss"] = pl_df
    if bs_df is not None:
        dfs["balancesheet"] = bs_df
    if cf_df is not None:
        dfs["cashflow"] = cf_df

    if dfs:
        failures, has_critical = validate_dataframes(dfs)
        critical = sum(1 for f in failures if f.severity == "CRITICAL")
        warnings = sum(1 for f in failures if f.severity == "WARNING")
        logger.info("DQ Results: %d CRITICAL, %d WARNING", critical, warnings)

        if has_critical:
            logger.error(
                "CRITICAL DQ failures found! "
                "Review output/validation_failures.csv"
            )
        else:
            logger.info(
                "No CRITICAL failures — data quality is acceptable ✅"
            )

    # ── Step 6: Show final row counts ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("LOAD RESULTS")
    print("=" * 60)

    tables = [
        "companies", "profitandloss", "balancesheet", "cashflow",
        "analysis", "documents", "prosandcons",
        "sectors", "stock_prices", "market_cap"
    ]

    total_rows = 0
    with sqlite3.connect(DB_PATH) as conn:
        for table in tables:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            total_rows += count
            icon = "✅" if count > 0 else "⚠️ "
            print(f"  {icon} {table:<25} {count:>6} rows")

    print(f"\n  Total rows loaded: {total_rows:,}")

    # ── Step 7: Save audit log ────────────────────────────────────────────
    audit_file = save_audit()

    # ── Step 8: FK integrity check ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("FOREIGN KEY CHECK")
    print("=" * 60)

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_key_check")
            violations = cursor.fetchall()

        if violations:
            print(f"  ⚠️  FK violations: {len(violations)}")
            for v in violations[:5]:
                print(f"     {v}")
        else:
            print("  ✅ FK check passed — no violations")

    except sqlite3.OperationalError as e:
        logger.warning("FK check skipped: %s", e)
        print("  ⚠️  FK check skipped")

    # ── Done ──────────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start_time).total_seconds()

    print("\n" + "=" * 60)
    print(f"✅ ETL Pipeline complete in {elapsed:.1f} seconds")
    print(f"📁 Database : {DB_PATH}")
    print(f"📄 Audit log: {audit_file}")
    print(f"📄 DQ report: {OUTPUT_PATH / 'validation_failures.csv'}")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_pipeline()