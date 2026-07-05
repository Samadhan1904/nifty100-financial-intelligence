"""
db_setup.py — Creates the SQLite database from schema.sql

This script:
1. Reads db/schema.sql
2. Creates nifty100.db with all 10 tables
3. Verifies all tables were created correctly

Run with:
    python src/etl/db_setup.py

Author: Samadhan
Sprint: 1 — Day 4
"""

import sqlite3
import logging
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import DB_PATH, PROJECT_ROOT

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Path to schema file
SCHEMA_FILE = PROJECT_ROOT / "db" / "schema.sql"

# Expected tables after setup
EXPECTED_TABLES = [
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
    "sectors",
    "stock_prices",
    "market_cap",
]


def create_database() -> bool:
    """
    Create SQLite database from schema.sql

    Returns:
        True if successful, False if any error occurred
    """
    logger.info("Creating database at: %s", DB_PATH)

    # Make sure data/ folder exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Read schema SQL file
    if not SCHEMA_FILE.exists():
        logger.error("Schema file not found: %s", SCHEMA_FILE)
        return False

    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
    logger.info("Schema file loaded: %d characters", len(schema_sql))

    # Connect to SQLite and execute schema
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")

            # Execute entire schema
            conn.executescript(schema_sql)

            # Commit
            conn.commit()

        logger.info("Database created successfully!")
        return True

    except sqlite3.Error as e:
        logger.error("Database creation failed: %s", e)
        return False


def verify_database() -> bool:
    """
    Verify all 10 tables were created correctly.

    Returns:
        True if all tables exist, False otherwise
    """
    logger.info("Verifying database structure...")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Get list of all tables
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table'
                ORDER BY name
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]

        # Check all expected tables exist
        missing = []
        for table in EXPECTED_TABLES:
            if table in existing_tables:
                logger.info("  ✓ Table exists: %s", table)
            else:
                logger.error("  ✗ Table MISSING: %s", table)
                missing.append(table)

        if missing:
            logger.error("Missing tables: %s", missing)
            return False

        logger.info(
            "All %d tables verified successfully!",
            len(EXPECTED_TABLES)
        )
        return True

    except sqlite3.Error as e:
        logger.error("Verification failed: %s", e)
        return False


def show_table_info():
    """
    Print column information for each table.
    Useful for debugging.
    """
    print("\n" + "=" * 60)
    print("DATABASE TABLE STRUCTURE")
    print("=" * 60)

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            for table in EXPECTED_TABLES:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()

                print(f"\n📋 {table.upper()}")
                print("-" * 40)
                for col in columns:
                    col_id   = col[0]
                    col_name = col[1]
                    col_type = col[2]
                    not_null = "NOT NULL" if col[3] else ""
                    pk       = "← PRIMARY KEY" if col[5] else ""
                    print(
                        f"  {col_name:<25} {col_type:<10} "
                        f"{not_null:<10} {pk}"
                    )

    except sqlite3.Error as e:
        logger.error("Could not show table info: %s", e)


def get_table_counts() -> dict:
    """
    Get row count for each table.
    After Day 5 load, these should all be > 0.

    Returns:
        Dictionary of {table_name: row_count}
    """
    counts = {}

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            for table in EXPECTED_TABLES:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]

    except sqlite3.Error as e:
        logger.error("Could not get counts: %s", e)

    return counts


def run_fk_check() -> bool:
    """
    Run SQLite foreign key integrity check.
    Should return 0 rows if all FKs are valid.

    Returns:
        True if FK check passes (0 violations)
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_key_check")
            violations = cursor.fetchall()

        if violations:
            logger.error(
                "FK check FAILED: %d violations found", len(violations)
            )
            for v in violations:
                logger.error("  Violation: %s", v)
            return False
        else:
            logger.info("FK check PASSED: No violations found")
            return True

    except sqlite3.Error as e:
        logger.error("FK check error: %s", e)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# MAIN — run when script is called directly
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Nifty 100 — Database Setup")
    print("=" * 60)

    # Step 1 — Create database
    success = create_database()
    if not success:
        print("\n❌ Database creation FAILED!")
        sys.exit(1)

    # Step 2 — Verify all tables exist
    verified = verify_database()
    if not verified:
        print("\n❌ Database verification FAILED!")
        sys.exit(1)

    # Step 3 — Show table structure
    show_table_info()

    # Step 4 — Show row counts (all 0 at this point — data loads on Day 5)
    print("\n" + "=" * 60)
    print("ROW COUNTS (all 0 now — data loads on Day 5)")
    print("=" * 60)
    counts = get_table_counts()
    for table, count in counts.items():
        print(f"  {table:<25} {count:>6} rows")

    # Step 5 — FK check
    print("\n" + "=" * 60)
    run_fk_check()

    print("\n✅ Database setup complete!")
    print(f"📁 Database file: {DB_PATH}")