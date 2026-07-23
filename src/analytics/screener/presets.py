"""
presets.py — Run all 6 preset screeners and save results.

Runs every preset from screener_config.yaml on real data.
Saves results to output/screener_output.xlsx with one
sheet per preset.

Run with:
    python src/analytics/screener/presets.py

Author: Samadhan
Sprint: 3 — Day 16
"""

import logging
import pandas as pd
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.config import OUTPUT_PATH
from src.analytics.screener.engine import ScreenerEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY COLUMNS
# ─────────────────────────────────────────────────────────────────────────────

DISPLAY_COLS = [
    "company_id",
    "company_name",
    "broad_sector",
    "year",
    "return_on_equity_pct",
    "return_on_capital_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "interest_coverage",
    "free_cash_flow_cr",
    "revenue_cagr_3yr",
    "revenue_cagr_5yr",
    "revenue_cagr_10yr",
    "pat_cagr_5yr",
    "capital_pattern",
    "cfo_quality_tier",
    "capex_tier",
]


# ─────────────────────────────────────────────────────────────────────────────
# RUN ALL PRESETS
# ─────────────────────────────────────────────────────────────────────────────

def run_all_presets(engine: ScreenerEngine) -> dict:
    """
    Run all 6 preset screeners.

    Returns:
        Dictionary of {preset_name: DataFrame}
    """
    presets = engine.get_available_presets()
    results = {}

    print("=" * 65)
    print("Running All 6 Preset Screeners")
    print("=" * 65)

    for preset_name in presets:
        desc = engine.get_preset_description(preset_name)
        print(f"\n── {preset_name.upper().replace('_', ' ')} ──")
        print(f"   {desc}")

        try:
            df = engine.screen_from_config(preset_name)

            # Select display columns that exist
            show_cols = [c for c in DISPLAY_COLS if c in df.columns]
            df_display = df[show_cols].copy()

            results[preset_name] = df_display

            print(f"   ✅ Found: {len(df_display)} companies")

            # Show top 5
            for i, (_, row) in enumerate(df_display.head(5).iterrows()):
                roe = row.get("return_on_equity_pct", "N/A")
                de  = row.get("debt_to_equity", "N/A")
                fcf = row.get("free_cash_flow_cr", "N/A")
                cagr= row.get("revenue_cagr_5yr", "N/A")

                fcf_str = (
                    f"{fcf:,.0f} Cr"
                    if isinstance(fcf, float) else "N/A"
                )
                cagr_str = (
                    f"{cagr:.1f}%"
                    if isinstance(cagr, float) else "N/A"
                )

                print(
                    f"   {i+1}. {row.get('company_id', ''):<12} "
                    f"ROE={roe}%  "
                    f"D/E={de}  "
                    f"FCF={fcf_str}  "
                    f"RevCAGR5yr={cagr_str}"
                )

        except Exception as e:
            logger.error(
                "Failed to run preset '%s': %s", preset_name, e
            )

    return results


# ─────────────────────────────────────────────────────────────────────────────
# SAVE TO EXCEL
# ─────────────────────────────────────────────────────────────────────────────

def save_to_excel(results: dict) -> Path:
    """
    Save all preset results to screener_output.xlsx.
    One sheet per preset.

    Returns:
        Path to saved file
    """
    output_file = OUTPUT_PATH / "screener_output.xlsx"

    logger.info("Saving screener results to Excel...")

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        for preset_name, df in results.items():
            # Sheet name max 31 chars
            sheet_name = preset_name[:31]

            if df.empty:
                logger.warning(
                    "Preset '%s' returned no results — skipping",
                    preset_name
                )
                continue

            # Round numeric columns
            numeric_cols = df.select_dtypes(
                include=["float64", "float32"]
            ).columns
            df[numeric_cols] = df[numeric_cols].round(2)

            df.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
            )

            logger.info(
                "Sheet '%s': %d rows", sheet_name, len(df)
            )

    logger.info("Saved to: %s", output_file)
    return output_file


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY REPORT
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(results: dict) -> None:
    """Print summary of all preset results."""
    print("\n" + "=" * 65)
    print("SCREENER RESULTS SUMMARY")
    print("=" * 65)

    total_unique = set()

    for preset_name, df in results.items():
        label = preset_name.replace("_", " ").title()
        count = len(df)
        print(f"  {label:<30} {count:>3} companies")

        if "company_id" in df.columns:
            total_unique.update(df["company_id"].tolist())

    print(f"\n  Total unique companies across all screens: "
          f"{len(total_unique)}")
    print(f"  Companies NOT in any screen:              "
          f"{91 - len(total_unique)}")

    # Business sense check
    print("\n  Business Sense Check:")

    # Quality compounder should have TCS
    qc = results.get("quality_compounder", pd.DataFrame())
    if not qc.empty and "company_id" in qc.columns:
        has_tcs = "TCS" in qc["company_id"].values
        print(f"    TCS in Quality Compounder:  "
              f"{'✅ YES' if has_tcs else '⚠️  NO'}")

    # Growth accelerator should have TRENT
    ga = results.get("growth_accelerator", pd.DataFrame())
    if not ga.empty and "company_id" in ga.columns:
        has_trent = "TRENT" in ga["company_id"].values
        print(f"    TRENT in Growth Accelerator: "
              f"{'✅ YES' if has_trent else '⚠️  NO'}")

    # Debt free should have TCS
    df_screen = results.get("debt_free_blue_chip", pd.DataFrame())
    if not df_screen.empty and "company_id" in df_screen.columns:
        has_tcs_df = "TCS" in df_screen["company_id"].values
        print(f"    TCS in Debt-Free Blue Chip:  "
              f"{'✅ YES' if has_tcs_df else '⚠️  NO'}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run_presets():
    """Run all presets and save results."""
    start = datetime.now()

    engine  = ScreenerEngine()
    results = run_all_presets(engine)

    output_file = save_to_excel(results)
    print_summary(results)

    elapsed = (datetime.now() - start).total_seconds()

    print("\n" + "=" * 65)
    print(f"✅ All 6 presets complete in {elapsed:.1f} seconds")
    print(f"📊 Results saved to: {output_file}")
    print("=" * 65)

    return results


if __name__ == "__main__":
    run_presets()