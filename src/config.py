"""
Central configuration loader.
Every other module imports settings from here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Project root = the nifty100/ folder
PROJECT_ROOT = Path(__file__).parent.parent

# Load the .env file
load_dotenv(PROJECT_ROOT / ".env")


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# File paths
DB_PATH              = PROJECT_ROOT / _get("DB_PATH", "data/nifty100.db")
RAW_DATA_PATH        = PROJECT_ROOT / _get("RAW_DATA_PATH", "data/raw")
SUPPORTING_DATA_PATH = PROJECT_ROOT / _get("SUPPORTING_DATA_PATH", "data/supporting")
OUTPUT_PATH          = PROJECT_ROOT / _get("OUTPUT_PATH", "output")
REPORTS_PATH         = PROJECT_ROOT / _get("REPORTS_PATH", "reports")

# Server
PORT      = int(_get("PORT", "8000"))
LOG_LEVEL = _get("LOG_LEVEL", "INFO")

# Flags
SIMULATED_DATA_FLAG = _get("SIMULATED_DATA_FLAG", "true").lower() == "true"

# Core Excel file paths (use header=1 when reading these)
COMPANIES_FILE    = RAW_DATA_PATH / "companies.xlsx"
PROFITLOSS_FILE   = RAW_DATA_PATH / "profitandloss.xlsx"
BALANCESHEET_FILE = RAW_DATA_PATH / "balancesheet.xlsx"
CASHFLOW_FILE     = RAW_DATA_PATH / "cashflow.xlsx"
ANALYSIS_FILE     = RAW_DATA_PATH / "analysis.xlsx"
DOCUMENTS_FILE    = RAW_DATA_PATH / "documents.xlsx"
PROSCONS_FILE     = RAW_DATA_PATH / "prosandcons.xlsx"

# Supplementary Excel file paths (use header=0 when reading these)
SECTORS_FILE          = SUPPORTING_DATA_PATH / "sectors.xlsx"
STOCK_PRICES_FILE     = SUPPORTING_DATA_PATH / "stock_prices.xlsx"
MARKET_CAP_FILE       = SUPPORTING_DATA_PATH / "market_cap.xlsx"
FINANCIAL_RATIOS_FILE = SUPPORTING_DATA_PATH / "financial_ratios.xlsx"
PEER_GROUPS_FILE      = SUPPORTING_DATA_PATH / "peer_groups.xlsx"

# Auto-create output directories when this file is imported
for _dir in [
    OUTPUT_PATH,
    REPORTS_PATH,
    REPORTS_PATH / "tearsheets",
    REPORTS_PATH / "sector",
    REPORTS_PATH / "portfolio",
    REPORTS_PATH / "radar_charts",
]:
    _dir.mkdir(parents=True, exist_ok=True)