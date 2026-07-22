"""
engine.py — Investment Screener Filter Engine

Reads thresholds from screener_config.yaml.
Filters financial_ratios table by any combination of KPIs.
Returns ranked DataFrame of matching companies.

Usage:
    from src.analytics.screener.engine import ScreenerEngine
    engine = ScreenerEngine()
    results = engine.screen(min_roe=15, max_de=1.0, min_fcf=0)

Run with:
    python src/analytics/screener/engine.py

Author: Samadhan
Sprint: 3 — Day 15
"""

import sqlite3
import logging
import yaml
import pandas as pd
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.config import DB_PATH, PROJECT_ROOT

logger = logging.getLogger(__name__)

# Path to screener config
CONFIG_FILE = PROJECT_ROOT / "config" / "screener_config.yaml"


# ─────────────────────────────────────────────────────────────────────────────
# LOAD CONFIG
# ─────────────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    """Load screener configuration from YAML file."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"screener_config.yaml not found at {CONFIG_FILE}"
        )
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA FROM DATABASE
# ─────────────────────────────────────────────────────────────────────────────

def load_latest_ratios() -> pd.DataFrame:
    """
    Load the latest year's financial ratios for each company.

    Returns one row per company (most recent year).
    Joins with companies and sectors for display.
    """
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("""
            SELECT
                fr.*,
                c.company_name,
                s.broad_sector,
                s.sub_sector
            FROM financial_ratios fr
            JOIN companies c ON fr.company_id = c.id
            LEFT JOIN sectors s ON fr.company_id = s.company_id
            WHERE fr.year = (
                SELECT MAX(year)
                FROM financial_ratios fr2
                WHERE fr2.company_id = fr.company_id
            )
            ORDER BY fr.company_id
        """, conn)

    logger.info(
        "Loaded latest ratios: %d companies", len(df)
    )
    return df


def load_all_ratios() -> pd.DataFrame:
    """Load all years of financial ratios (for trend filtering)."""
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("""
            SELECT fr.*, c.company_name, s.broad_sector
            FROM financial_ratios fr
            JOIN companies c ON fr.company_id = c.id
            LEFT JOIN sectors s ON fr.company_id = s.company_id
            ORDER BY fr.company_id, fr.year
        """, conn)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SCREENER ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class ScreenerEngine:
    """
    Investment Screener Engine.

    Filters financial_ratios by KPI thresholds.
    Returns ranked DataFrame of matching companies.

    Usage:
        engine  = ScreenerEngine()
        results = engine.screen(min_roe=15, max_de=1.0)
        print(results[["company_id", "company_name", "return_on_equity_pct"]])
    """

    def __init__(self):
        self.config      = load_config()
        self.col_map     = self.config.get("filter_column_map", {})
        self._df_latest  = None   # cached latest ratios
        logger.info("ScreenerEngine initialized")

    def _get_latest_ratios(self) -> pd.DataFrame:
        """Get latest ratios (cached after first load)."""
        if self._df_latest is None:
            self._df_latest = load_latest_ratios()
        return self._df_latest.copy()

    def screen(
        self,
        sector: Optional[str]  = None,
        min_roe:               Optional[float] = None,
        max_de:                Optional[float] = None,
        min_fcf:               Optional[float] = None,
        min_revenue_cagr_5yr:  Optional[float] = None,
        min_revenue_cagr_3yr:  Optional[float] = None,
        min_pat_cagr_5yr:      Optional[float] = None,
        min_npm:               Optional[float] = None,
        min_roce:              Optional[float] = None,
        max_de_strict:         Optional[float] = None,
        rank_by:               str = "return_on_equity_pct",
        top_n:                 Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Screen companies by KPI thresholds.

        Args:
            sector:               Filter by broad sector
            min_roe:              Minimum ROE %
            max_de:               Maximum D/E ratio
            min_fcf:              Minimum FCF (Crore)
            min_revenue_cagr_5yr: Minimum 5yr revenue CAGR %
            min_revenue_cagr_3yr: Minimum 3yr revenue CAGR %
            min_pat_cagr_5yr:     Minimum 5yr PAT CAGR %
            min_npm:              Minimum Net Profit Margin %
            min_roce:             Minimum ROCE %
            rank_by:              Column to sort results by
            top_n:                Return only top N results

        Returns:
            Filtered and ranked DataFrame
        """
        df = self._get_latest_ratios()
        original_count = len(df)

        # ── Sector filter ────────────────────────────────────────────────
        if sector:
            df = df[df["broad_sector"] == sector]
            logger.info(
                "Sector filter '%s': %d → %d companies",
                sector, original_count, len(df)
            )

        # ── KPI filters ──────────────────────────────────────────────────
        filters_applied = []

        if min_roe is not None:
            before = len(df)
            df = df[
                df["return_on_equity_pct"].notna() &
                (df["return_on_equity_pct"] >= min_roe)
            ]
            filters_applied.append(f"ROE>={min_roe}%")
            logger.info(
                "ROE >= %s: %d → %d", min_roe, before, len(df)
            )

        if max_de is not None:
            before = len(df)
            df = df[
                df["debt_to_equity"].notna() &
                (df["debt_to_equity"] <= max_de)
            ]
            filters_applied.append(f"D/E<={max_de}")
            logger.info(
                "D/E <= %s: %d → %d", max_de, before, len(df)
            )

        if min_fcf is not None:
            before = len(df)
            df = df[
                df["free_cash_flow_cr"].notna() &
                (df["free_cash_flow_cr"] >= min_fcf)
            ]
            filters_applied.append(f"FCF>={min_fcf}")
            logger.info(
                "FCF >= %s: %d → %d", min_fcf, before, len(df)
            )

        if min_revenue_cagr_5yr is not None:
            before = len(df)
            df = df[
                df["revenue_cagr_5yr"].notna() &
                (df["revenue_cagr_5yr"] >= min_revenue_cagr_5yr)
            ]
            filters_applied.append(
                f"RevCAGR5yr>={min_revenue_cagr_5yr}%"
            )
            logger.info(
                "Rev CAGR 5yr >= %s: %d → %d",
                min_revenue_cagr_5yr, before, len(df)
            )

        if min_revenue_cagr_3yr is not None:
            before = len(df)
            df = df[
                df["revenue_cagr_3yr"].notna() &
                (df["revenue_cagr_3yr"] >= min_revenue_cagr_3yr)
            ]
            filters_applied.append(
                f"RevCAGR3yr>={min_revenue_cagr_3yr}%"
            )

        if min_pat_cagr_5yr is not None:
            before = len(df)
            df = df[
                df["pat_cagr_5yr"].notna() &
                (df["pat_cagr_5yr"] >= min_pat_cagr_5yr)
            ]
            filters_applied.append(
                f"PATCAGR5yr>={min_pat_cagr_5yr}%"
            )
            logger.info(
                "PAT CAGR 5yr >= %s: %d → %d",
                min_pat_cagr_5yr, before, len(df)
            )

        if min_npm is not None:
            before = len(df)
            df = df[
                df["net_profit_margin_pct"].notna() &
                (df["net_profit_margin_pct"] >= min_npm)
            ]
            filters_applied.append(f"NPM>={min_npm}%")
            logger.info(
                "NPM >= %s: %d → %d", min_npm, before, len(df)
            )

        if min_roce is not None:
            before = len(df)
            df = df[
                df["return_on_capital_pct"].notna() &
                (df["return_on_capital_pct"] >= min_roce)
            ]
            filters_applied.append(f"ROCE>={min_roce}%")

        # ── Rank results ─────────────────────────────────────────────────
        if rank_by in df.columns:
            df = df.sort_values(rank_by, ascending=False)
        else:
            df = df.sort_values(
                "return_on_equity_pct",
                ascending=False,
                na_position="last"
            )

        # ── Top N ────────────────────────────────────────────────────────
        if top_n:
            df = df.head(top_n)

        logger.info(
            "Screen complete: %d companies match [%s]",
            len(df),
            ", ".join(filters_applied) if filters_applied else "no filters"
        )

        return df.reset_index(drop=True)

    def screen_from_config(self, preset_name: str) -> pd.DataFrame:
        """
        Run a preset screener from screener_config.yaml.

        Args:
            preset_name: Key in presets section of config
                         e.g. "quality_compounder"

        Returns:
            Filtered DataFrame

        Raises:
            KeyError if preset_name not found in config
        """
        presets = self.config.get("presets", {})

        if preset_name not in presets:
            available = list(presets.keys())
            raise KeyError(
                f"Preset '{preset_name}' not found. "
                f"Available: {available}"
            )

        preset   = presets[preset_name]
        filters  = preset.get("filters", {})
        rank_by  = preset.get("rank_by", "return_on_equity_pct")
        desc     = preset.get("description", "")

        logger.info(
            "Running preset '%s': %s", preset_name, desc
        )

        # Map filter names to screen() parameters
        screen_kwargs = {}
        for filter_name, value in filters.items():
            screen_kwargs[filter_name] = value

        screen_kwargs["rank_by"] = rank_by
        return self.screen(**screen_kwargs)

    def get_available_presets(self) -> list:
        """Return list of available preset names."""
        return list(self.config.get("presets", {}).keys())

    def get_preset_description(self, preset_name: str) -> str:
        """Return description for a preset."""
        presets = self.config.get("presets", {})
        preset  = presets.get(preset_name, {})
        return preset.get("description", "")


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY HELPER
# ─────────────────────────────────────────────────────────────────────────────

def display_results(
    df: pd.DataFrame,
    preset_name: str = "",
    max_rows: int = 20,
) -> None:
    """Pretty print screener results."""
    print(f"\n  {'─' * 60}")
    if preset_name:
        print(f"  Preset: {preset_name.upper().replace('_', ' ')}")
    print(f"  Results: {len(df)} companies")
    print(f"  {'─' * 60}")

    display_cols = [
        "company_id", "company_name", "broad_sector",
        "return_on_equity_pct", "debt_to_equity",
        "net_profit_margin_pct", "free_cash_flow_cr",
        "revenue_cagr_5yr", "capital_pattern",
    ]

    # Only show columns that exist
    show_cols = [c for c in display_cols if c in df.columns]

    for i, (_, row) in enumerate(df.head(max_rows).iterrows()):
        print(
            f"  {i+1:>2}. {row.get('company_id', ''):<12} "
            f"{str(row.get('company_name', ''))[:25]:<25} "
            f"ROE={row.get('return_on_equity_pct', 'N/A')}%  "
            f"D/E={row.get('debt_to_equity', 'N/A')}  "
            f"FCF={row.get('free_cash_flow_cr', 'N/A'):,.0f} Cr"
            if isinstance(row.get('free_cash_flow_cr'), float)
            else
            f"  {i+1:>2}. {row.get('company_id', ''):<12} "
            f"ROE={row.get('return_on_equity_pct', 'N/A')}%"
        )


# ─────────────────────────────────────────────────────────────────────────────
# QUICK TEST
# python src/analytics/screener/engine.py
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("Testing Screener Engine")
    print("=" * 60)

    engine = ScreenerEngine()

    print(f"\nAvailable presets: {engine.get_available_presets()}")

    # Test 1 — Custom screen
    print("\n── Test 1: Custom Screen (ROE>15, D/E<1, FCF>0) ──")
    results = engine.screen(
        min_roe=15,
        max_de=1.0,
        min_fcf=0,
    )
    print(f"  Found: {len(results)} companies")
    for _, row in results.head(5).iterrows():
        print(
            f"  {row['company_id']:<12} "
            f"ROE={row.get('return_on_equity_pct', 'N/A')}%  "
            f"D/E={row.get('debt_to_equity', 'N/A')}"
        )

    # Test 2 — Preset screener
    print("\n── Test 2: Quality Compounder Preset ──")
    results2 = engine.screen_from_config("quality_compounder")
    print(f"  Found: {len(results2)} companies")
    for _, row in results2.head(5).iterrows():
        print(
            f"  {row['company_id']:<12} "
            f"ROE={row.get('return_on_equity_pct', 'N/A')}%  "
            f"D/E={row.get('debt_to_equity', 'N/A')}  "
            f"Rev CAGR 5yr={row.get('revenue_cagr_5yr', 'N/A')}%"
        )

    # Test 3 — Debt free
    print("\n── Test 3: Debt-Free Blue Chip ──")
    results3 = engine.screen_from_config("debt_free_blue_chip")
    print(f"  Found: {len(results3)} companies")
    for _, row in results3.head(5).iterrows():
        print(
            f"  {row['company_id']:<12} "
            f"ROE={row.get('return_on_equity_pct', 'N/A')}%  "
            f"D/E={row.get('debt_to_equity', 'N/A')}"
        )

    # Test 4 — Growth accelerator
    print("\n── Test 4: Growth Accelerator ──")
    results4 = engine.screen_from_config("growth_accelerator")
    print(f"  Found: {len(results4)} companies")

    # Test 5 — Sector filter
    print("\n── Test 5: IT Sector Only ──")
    results5 = engine.screen(
        sector="Information Technology",
        min_roe=20,
    )
    print(f"  Found: {len(results5)} IT companies with ROE>20%")
    for _, row in results5.iterrows():
        print(
            f"  {row['company_id']:<12} "
            f"ROE={row.get('return_on_equity_pct', 'N/A')}%"
        )

    print("\n✅ Screener Engine working correctly!")