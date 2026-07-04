"""
validator.py — 16 Data Quality Rules for Nifty 100 ETL Pipeline.

Runs on every DataFrame before it is loaded into SQLite.
Produces validation_failures.csv with all violations found.

Severity levels:
    CRITICAL → Data is unusable. Halt load for this table.
    WARNING  → Data has issues but load can continue.
    INFO     → Informational only. No action needed.

Author: Samadhan
Sprint: 1 — Day 3
"""

import re
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

# Import config for output path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.config import OUTPUT_PATH

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION RESULT — one object per violation found
# ─────────────────────────────────────────────────────────────────────────────

class ValidationResult:
    """
    Stores one data quality violation.

    Example:
        rule_id    = "DQ-04"
        rule_name  = "Balance Sheet Balance"
        company_id = "TCS"
        year       = "2023-03"
        field      = "total_assets"
        issue      = "Assets 1000 != Liabilities 1050 (diff 4.76%)"
        severity   = "WARNING"
    """

    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        severity: str,
        company_id: str = "",
        year: str = "",
        field: str = "",
        issue: str = "",
    ):
        self.rule_id    = rule_id
        self.rule_name  = rule_name
        self.severity   = severity
        self.company_id = company_id
        self.year       = year
        self.field      = field
        self.issue      = issue
        self.timestamp  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        """Convert to dictionary for saving to CSV."""
        return {
            "rule_id":    self.rule_id,
            "rule_name":  self.rule_name,
            "severity":   self.severity,
            "company_id": self.company_id,
            "year":       self.year,
            "field":      self.field,
            "issue":      self.issue,
            "timestamp":  self.timestamp,
        }

    def __repr__(self):
        return (
            f"[{self.severity}] {self.rule_id} | "
            f"{self.company_id} {self.year} | "
            f"{self.issue}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN VALIDATOR CLASS
# ─────────────────────────────────────────────────────────────────────────────

class DataValidator:
    """
    Runs all 16 DQ rules on the loaded DataFrames.

    Usage:
        validator = DataValidator()
        failures  = validator.validate_all(dataframes)
        validator.save_failures(failures)
    """

    def __init__(self):
        self.failures: list[ValidationResult] = []

    # ─────────────────────────────────────────────────────────────────────
    # PUBLIC METHOD: validate_all()
    # ─────────────────────────────────────────────────────────────────────

    def validate_all(self, dfs: dict) -> list[ValidationResult]:
        """
        Run all 16 DQ rules on the provided DataFrames.

        Args:
            dfs: Dictionary of DataFrames
                 Keys: "companies", "profitandloss", "balancesheet",
                       "cashflow", "analysis", "documents", "prosandcons"

        Returns:
            List of ValidationResult objects (one per violation found)
        """
        self.failures = []

        logger.info("Starting data quality validation...")

        # Get individual DataFrames (use empty DF if not provided)
        companies     = dfs.get("companies",     pd.DataFrame())
        profitandloss = dfs.get("profitandloss", pd.DataFrame())
        balancesheet  = dfs.get("balancesheet",  pd.DataFrame())
        cashflow      = dfs.get("cashflow",      pd.DataFrame())

        # ── Run all 16 rules ──────────────────────────────────────────────
        self._dq01_company_pk_uniqueness(companies)
        self._dq02_annual_pk_uniqueness(profitandloss, balancesheet, cashflow)
        self._dq03_fk_integrity(companies, profitandloss, balancesheet, cashflow)
        self._dq04_balance_sheet_balance(balancesheet)
        self._dq05_opm_cross_check(profitandloss)
        self._dq06_positive_sales(profitandloss)
        self._dq07_year_format(profitandloss, balancesheet, cashflow)
        self._dq08_ticker_format(companies, profitandloss, balancesheet, cashflow)
        self._dq09_net_cash_check(cashflow)
        self._dq10_non_negative_fixed_assets(balancesheet)
        self._dq11_tax_rate_range(profitandloss)
        self._dq12_dividend_payout_cap(profitandloss)
        self._dq14_eps_sign_consistency(profitandloss)
        self._dq15_bse_balance_strict(balancesheet)
        self._dq16_coverage_check(profitandloss, balancesheet, cashflow)

        # Summary
        critical = sum(1 for f in self.failures if f.severity == "CRITICAL")
        warnings = sum(1 for f in self.failures if f.severity == "WARNING")
        logger.info(
            "Validation complete: %d CRITICAL, %d WARNING failures",
            critical, warnings
        )

        return self.failures

    # ─────────────────────────────────────────────────────────────────────
    # SAVE RESULTS TO CSV
    # ─────────────────────────────────────────────────────────────────────

    def save_failures(self, failures: list[ValidationResult]) -> Path:
        """
        Save all validation failures to output/validation_failures.csv

        Args:
            failures: List of ValidationResult objects

        Returns:
            Path to the saved CSV file
        """
        output_file = OUTPUT_PATH / "validation_failures.csv"

        if not failures:
            logger.info("No validation failures found!")
            # Create empty file with headers
            pd.DataFrame(columns=[
                "rule_id", "rule_name", "severity",
                "company_id", "year", "field", "issue", "timestamp"
            ]).to_csv(output_file, index=False)
        else:
            df = pd.DataFrame([f.to_dict() for f in failures])
            df.to_csv(output_file, index=False)
            logger.info("Saved %d failures to %s", len(failures), output_file)

        return output_file

    def get_critical_failures(self) -> list[ValidationResult]:
        """Return only CRITICAL severity failures."""
        return [f for f in self.failures if f.severity == "CRITICAL"]

    def has_critical_failures(self) -> bool:
        """Return True if any CRITICAL failures exist."""
        return any(f.severity == "CRITICAL" for f in self.failures)

    # =========================================================================
    # THE 16 DQ RULES
    # =========================================================================

    # ── DQ-01: Company PK Uniqueness ─────────────────────────────────────────

    def _dq01_company_pk_uniqueness(self, companies: pd.DataFrame):
        """
        DQ-01: companies.id must be unique — no duplicate tickers allowed.
        Severity: CRITICAL

        Why: If two rows have id="TCS", every join will return double rows.
        """
        if companies.empty:
            return

        if "id" not in companies.columns:
            return

        duplicates = companies[companies["id"].duplicated(keep=False)]

        if not duplicates.empty:
            dup_ids = duplicates["id"].unique().tolist()
            self.failures.append(ValidationResult(
                rule_id    = "DQ-01",
                rule_name  = "Company PK Uniqueness",
                severity   = "CRITICAL",
                field      = "id",
                issue      = f"Duplicate company IDs found: {dup_ids}",
            ))
            logger.error("DQ-01 CRITICAL: Duplicate tickers: %s", dup_ids)
        else:
            logger.info("DQ-01 PASSED: All %d company IDs are unique", len(companies))

    # ── DQ-02: Annual PK Uniqueness ──────────────────────────────────────────

    def _dq02_annual_pk_uniqueness(
        self,
        profitandloss: pd.DataFrame,
        balancesheet: pd.DataFrame,
        cashflow: pd.DataFrame,
    ):
        """
        DQ-02: No duplicate (company_id, year) pairs in time-series tables.
        Severity: CRITICAL

        Why: Duplicate rows cause double-counting in ratio calculations.
        """
        tables = {
            "profitandloss": profitandloss,
            "balancesheet":  balancesheet,
            "cashflow":      cashflow,
        }

        for table_name, df in tables.items():
            if df.empty:
                continue
            if "company_id" not in df.columns or "year" not in df.columns:
                continue

            duplicates = df[df.duplicated(
                subset=["company_id", "year"], keep=False
            )]

            if not duplicates.empty:
                count = len(duplicates)
                self.failures.append(ValidationResult(
                    rule_id    = "DQ-02",
                    rule_name  = "Annual PK Uniqueness",
                    severity   = "CRITICAL",
                    field      = "company_id, year",
                    issue      = f"{table_name}: {count} duplicate (company_id, year) pairs found",
                ))
                logger.error(
                    "DQ-02 CRITICAL: %s has %d duplicate rows", table_name, count
                )
            else:
                logger.info("DQ-02 PASSED: %s has no duplicate rows", table_name)

    # ── DQ-03: FK Integrity ───────────────────────────────────────────────────

    def _dq03_fk_integrity(
        self,
        companies: pd.DataFrame,
        profitandloss: pd.DataFrame,
        balancesheet: pd.DataFrame,
        cashflow: pd.DataFrame,
    ):
        """
        DQ-03: All company_id values in child tables must exist in companies.id
        Severity: CRITICAL

        Why: Orphan rows (company_id not in companies) break all joins.
        """
        if companies.empty or "id" not in companies.columns:
            return

        valid_ids = set(companies["id"].dropna().unique())

        tables = {
            "profitandloss": profitandloss,
            "balancesheet":  balancesheet,
            "cashflow":      cashflow,
        }

        for table_name, df in tables.items():
            if df.empty:
                continue
            if "company_id" not in df.columns:
                continue

            child_ids   = set(df["company_id"].dropna().unique())
            orphan_ids  = child_ids - valid_ids

            if orphan_ids:
                self.failures.append(ValidationResult(
                    rule_id    = "DQ-03",
                    rule_name  = "FK Integrity",
                    severity   = "CRITICAL",
                    field      = "company_id",
                    issue      = f"{table_name}: orphan IDs not in companies: {sorted(orphan_ids)}",
                ))
                logger.error(
                    "DQ-03 CRITICAL: %s has orphan IDs: %s",
                    table_name, orphan_ids
                )
            else:
                logger.info(
                    "DQ-03 PASSED: All %s company_ids exist in companies",
                    table_name
                )

    # ── DQ-04: Balance Sheet Balance ─────────────────────────────────────────

    def _dq04_balance_sheet_balance(self, balancesheet: pd.DataFrame):
        """
        DQ-04: |total_assets - total_liabilities| / total_assets < 1%
        Severity: WARNING

        Why: A balance sheet must balance. Large differences = data error.
        """
        if balancesheet.empty:
            return

        required = ["company_id", "year", "total_assets", "total_liabilities"]
        if not all(c in balancesheet.columns for c in required):
            return

        for _, row in balancesheet.iterrows():
            assets      = row.get("total_assets", 0)
            liabilities = row.get("total_liabilities", 0)

            # Skip rows where assets is zero or NaN
            if pd.isna(assets) or assets == 0:
                continue

            diff_pct = abs(assets - liabilities) / abs(assets) * 100

            if diff_pct >= 1.0:
                self.failures.append(ValidationResult(
                    rule_id    = "DQ-04",
                    rule_name  = "Balance Sheet Balance",
                    severity   = "WARNING",
                    company_id = str(row.get("company_id", "")),
                    year       = str(row.get("year", "")),
                    field      = "total_assets vs total_liabilities",
                    issue      = (
                        f"Assets={assets:.0f} Liabilities={liabilities:.0f} "
                        f"diff={diff_pct:.2f}% (threshold 1%)"
                    ),
                ))

    # ── DQ-05: OPM Cross-Check ───────────────────────────────────────────────

    def _dq05_opm_cross_check(self, profitandloss: pd.DataFrame):
        """
        DQ-05: |opm_percentage - (operating_profit/sales*100)| < 1%
        Severity: WARNING

        Why: The source file has a pre-computed OPM%. We verify it
             matches our own calculation. Large differences = data issue.
        """
        if profitandloss.empty:
            return

        required = ["company_id", "year", "opm_percentage",
                    "operating_profit", "sales"]
        if not all(c in profitandloss.columns for c in required):
            return

        for _, row in profitandloss.iterrows():
            opm_source = row.get("opm_percentage")
            op_profit  = row.get("operating_profit")
            sales      = row.get("sales")

            # Skip if any value is missing or sales is zero
            if any(pd.isna(v) for v in [opm_source, op_profit, sales]):
                continue
            if sales == 0:
                continue

            opm_computed = (op_profit / sales) * 100
            diff = abs(opm_source - opm_computed)

            if diff > 1.0:
                self.failures.append(ValidationResult(
                    rule_id    = "DQ-05",
                    rule_name  = "OPM Cross-Check",
                    severity   = "WARNING",
                    company_id = str(row.get("company_id", "")),
                    year       = str(row.get("year", "")),
                    field      = "opm_percentage",
                    issue      = (
                        f"Source OPM={opm_source:.2f}% "
                        f"Computed OPM={opm_computed:.2f}% "
                        f"diff={diff:.2f}%"
                    ),
                ))

    # ── DQ-06: Positive Sales ────────────────────────────────────────────────

    def _dq06_positive_sales(self, profitandloss: pd.DataFrame):
        """
        DQ-06: sales > 0 for all non-bank companies.
        Severity: WARNING

        Why: Zero or negative sales is almost always a data error.
        """
        if profitandloss.empty:
            return

        if "sales" not in profitandloss.columns:
            return

        bad_rows = profitandloss[
            profitandloss["sales"].notna() &
            (profitandloss["sales"] <= 0)
        ]

        for _, row in bad_rows.iterrows():
            self.failures.append(ValidationResult(
                rule_id    = "DQ-06",
                rule_name  = "Positive Sales",
                severity   = "WARNING",
                company_id = str(row.get("company_id", "")),
                year       = str(row.get("year", "")),
                field      = "sales",
                issue      = f"sales={row['sales']} (must be > 0)",
            ))

    # ── DQ-07: Year Format ───────────────────────────────────────────────────

    def _dq07_year_format(
        self,
        profitandloss: pd.DataFrame,
        balancesheet: pd.DataFrame,
        cashflow: pd.DataFrame,
    ):
        """
        DQ-07: All year values must match YYYY-MM format after normalisation.
        Severity: CRITICAL

        Why: Wrong year format breaks all time-series joins.
        """
        year_pattern = re.compile(r"^\d{4}-\d{2}$")

        tables = {
            "profitandloss": profitandloss,
            "balancesheet":  balancesheet,
            "cashflow":      cashflow,
        }

        for table_name, df in tables.items():
            if df.empty or "year" not in df.columns:
                continue

            for _, row in df.iterrows():
                year_val = str(row.get("year", ""))

                if year_val in ("PARSE_ERROR", "nan", ""):
                    self.failures.append(ValidationResult(
                        rule_id    = "DQ-07",
                        rule_name  = "Year Format",
                        severity   = "CRITICAL",
                        company_id = str(row.get("company_id", "")),
                        year       = year_val,
                        field      = "year",
                        issue      = f"{table_name}: unparseable year '{year_val}'",
                    ))
                elif not year_pattern.match(year_val):
                    self.failures.append(ValidationResult(
                        rule_id    = "DQ-07",
                        rule_name  = "Year Format",
                        severity   = "CRITICAL",
                        company_id = str(row.get("company_id", "")),
                        year       = year_val,
                        field      = "year",
                        issue      = f"{table_name}: year '{year_val}' does not match YYYY-MM",
                    ))

    # ── DQ-08: Ticker Format ─────────────────────────────────────────────────

    def _dq08_ticker_format(
        self,
        companies: pd.DataFrame,
        profitandloss: pd.DataFrame,
        balancesheet: pd.DataFrame,
        cashflow: pd.DataFrame,
    ):
        """
        DQ-08: company_id must be 2-12 chars, uppercase, stripped.
        Severity: CRITICAL

        Why: Tickers outside this range are likely data errors.
        """
        all_dfs = {
            "companies":     companies,
            "profitandloss": profitandloss,
            "balancesheet":  balancesheet,
            "cashflow":      cashflow,
        }

        id_col = {
            "companies":     "id",
            "profitandloss": "company_id",
            "balancesheet":  "company_id",
            "cashflow":      "company_id",
        }

        for table_name, df in all_dfs.items():
            if df.empty:
                continue

            col = id_col[table_name]
            if col not in df.columns:
                continue

            for _, row in df.iterrows():
                ticker = str(row.get(col, "")).strip()

                if len(ticker) < 2 or len(ticker) > 12:
                    self.failures.append(ValidationResult(
                        rule_id    = "DQ-08",
                        rule_name  = "Ticker Format",
                        severity   = "CRITICAL",
                        company_id = ticker,
                        field      = col,
                        issue      = (
                            f"{table_name}: ticker '{ticker}' "
                            f"length {len(ticker)} (must be 2-12)"
                        ),
                    ))

    # ── DQ-09: Net Cash Check ────────────────────────────────────────────────

    def _dq09_net_cash_check(self, cashflow: pd.DataFrame):
        """
        DQ-09: |net_cash_flow - (CFO + CFI + CFF)| <= 10 Crore tolerance
        Severity: WARNING

        Why: Net cash flow must equal the sum of its three components.
        """
        if cashflow.empty:
            return

        required = [
            "company_id", "year",
            "operating_activity", "investing_activity",
            "financing_activity", "net_cash_flow"
        ]
        if not all(c in cashflow.columns for c in required):
            return

        for _, row in cashflow.iterrows():
            cfo = row.get("operating_activity",  0) or 0
            cfi = row.get("investing_activity",   0) or 0
            cff = row.get("financing_activity",   0) or 0
            ncf = row.get("net_cash_flow",        0) or 0

            if any(pd.isna(v) for v in [cfo, cfi, cff, ncf]):
                continue

            computed = cfo + cfi + cff
            diff     = abs(ncf - computed)

            if diff > 10:
                self.failures.append(ValidationResult(
                    rule_id    = "DQ-09",
                    rule_name  = "Net Cash Check",
                    severity   = "WARNING",
                    company_id = str(row.get("company_id", "")),
                    year       = str(row.get("year", "")),
                    field      = "net_cash_flow",
                    issue      = (
                        f"net_cash_flow={ncf:.0f} "
                        f"CFO+CFI+CFF={computed:.0f} "
                        f"diff={diff:.0f} Cr (threshold 10 Cr)"
                    ),
                ))

    # ── DQ-10: Non-Negative Fixed Assets ─────────────────────────────────────

    def _dq10_non_negative_fixed_assets(self, balancesheet: pd.DataFrame):
        """
        DQ-10: fixed_assets >= 0
        Severity: WARNING

        Why: Negative fixed assets is a data entry error.
        """
        if balancesheet.empty:
            return

        if "fixed_assets" not in balancesheet.columns:
            return

        bad_rows = balancesheet[
            balancesheet["fixed_assets"].notna() &
            (balancesheet["fixed_assets"] < 0)
        ]

        for _, row in bad_rows.iterrows():
            self.failures.append(ValidationResult(
                rule_id    = "DQ-10",
                rule_name  = "Non-Negative Fixed Assets",
                severity   = "WARNING",
                company_id = str(row.get("company_id", "")),
                year       = str(row.get("year", "")),
                field      = "fixed_assets",
                issue      = f"fixed_assets={row['fixed_assets']} (must be >= 0)",
            ))

    # ── DQ-11: Tax Rate Range ────────────────────────────────────────────────

    def _dq11_tax_rate_range(self, profitandloss: pd.DataFrame):
        """
        DQ-11: 0 <= tax_percentage <= 60
        Severity: WARNING

        Why: Tax rates outside 0-60% are almost certainly data errors.
             Indian corporate tax is typically 22-35%.
        """
        if profitandloss.empty:
            return

        if "tax_percentage" not in profitandloss.columns:
            return

        bad_rows = profitandloss[
            profitandloss["tax_percentage"].notna() &
            (
                (profitandloss["tax_percentage"] < 0) |
                (profitandloss["tax_percentage"] > 60)
            )
        ]

        for _, row in bad_rows.iterrows():
            self.failures.append(ValidationResult(
                rule_id    = "DQ-11",
                rule_name  = "Tax Rate Range",
                severity   = "WARNING",
                company_id = str(row.get("company_id", "")),
                year       = str(row.get("year", "")),
                field      = "tax_percentage",
                issue      = (
                    f"tax_percentage={row['tax_percentage']} "
                    f"(must be 0-60)"
                ),
            ))

    # ── DQ-12: Dividend Payout Cap ───────────────────────────────────────────

    def _dq12_dividend_payout_cap(self, profitandloss: pd.DataFrame):
        """
        DQ-12: dividend_payout <= 200%
        Severity: WARNING

        Why: Payout > 200% is almost certainly a data entry error.
             (>100% can happen in low-profit years — that's normal)
        """
        if profitandloss.empty:
            return

        if "dividend_payout" not in profitandloss.columns:
            return

        bad_rows = profitandloss[
            profitandloss["dividend_payout"].notna() &
            (profitandloss["dividend_payout"] > 200)
        ]

        for _, row in bad_rows.iterrows():
            self.failures.append(ValidationResult(
                rule_id    = "DQ-12",
                rule_name  = "Dividend Payout Cap",
                severity   = "WARNING",
                company_id = str(row.get("company_id", "")),
                year       = str(row.get("year", "")),
                field      = "dividend_payout",
                issue      = (
                    f"dividend_payout={row['dividend_payout']}% "
                    f"(likely error, threshold 200%)"
                ),
            ))

    # ── DQ-14: EPS Sign Consistency ──────────────────────────────────────────

    def _dq14_eps_sign_consistency(self, profitandloss: pd.DataFrame):
        """
        DQ-14: eps > 0 when net_profit > 0
        Severity: WARNING

        Why: If company made profit, EPS must be positive.
             Mismatch indicates data issue.
        """
        if profitandloss.empty:
            return

        required = ["company_id", "year", "eps", "net_profit"]
        if not all(c in profitandloss.columns for c in required):
            return

        for _, row in profitandloss.iterrows():
            eps    = row.get("eps")
            profit = row.get("net_profit")

            if pd.isna(eps) or pd.isna(profit):
                continue

            # Profit is positive but EPS is not positive
            if profit > 0 and eps <= 0:
                self.failures.append(ValidationResult(
                    rule_id    = "DQ-14",
                    rule_name  = "EPS Sign Consistency",
                    severity   = "WARNING",
                    company_id = str(row.get("company_id", "")),
                    year       = str(row.get("year", "")),
                    field      = "eps",
                    issue      = (
                        f"net_profit={profit:.0f} is positive "
                        f"but eps={eps} is not positive"
                    ),
                ))

    # ── DQ-15: BSE Balance Strict ────────────────────────────────────────────

    def _dq15_bse_balance_strict(self, balancesheet: pd.DataFrame):
        """
        DQ-15: total_liabilities == total_assets (strict, informational)
        Severity: INFO

        Why: After DQ-04 flags the warnings, this gives exact count
             of rows where balance sheet is perfectly balanced.
        """
        if balancesheet.empty:
            return

        required = ["total_assets", "total_liabilities"]
        if not all(c in balancesheet.columns for c in required):
            return

        unbalanced = balancesheet[
            balancesheet["total_assets"].notna() &
            balancesheet["total_liabilities"].notna() &
            (balancesheet["total_assets"] != balancesheet["total_liabilities"])
        ]

        if not unbalanced.empty:
            self.failures.append(ValidationResult(
                rule_id  = "DQ-15",
                rule_name= "BSE Balance Strict",
                severity = "INFO",
                field    = "total_assets vs total_liabilities",
                issue    = (
                    f"{len(unbalanced)} rows where "
                    f"total_assets != total_liabilities (informational)"
                ),
            ))

    # ── DQ-16: Coverage Check ────────────────────────────────────────────────

    def _dq16_coverage_check(
        self,
        profitandloss: pd.DataFrame,
        balancesheet: pd.DataFrame,
        cashflow: pd.DataFrame,
    ):
        """
        DQ-16: Each company must have >= 5 years of P&L, BS, CF records.
        Severity: WARNING

        Why: Companies with < 5 years cannot have 5yr CAGR computed.
             Companies with < 3 years are excluded from all CAGR.
        """
        tables = {
            "profitandloss": profitandloss,
            "balancesheet":  balancesheet,
            "cashflow":      cashflow,
        }

        for table_name, df in tables.items():
            if df.empty or "company_id" not in df.columns:
                continue

            year_counts = df.groupby("company_id")["year"].count()
            low_coverage = year_counts[year_counts < 5]

            for company_id, count in low_coverage.items():
                self.failures.append(ValidationResult(
                    rule_id    = "DQ-16",
                    rule_name  = "Coverage Check",
                    severity   = "WARNING",
                    company_id = str(company_id),
                    field      = "year",
                    issue      = (
                        f"{table_name}: only {count} years of data "
                        f"(minimum 5 required for CAGR)"
                    ),
                ))


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def validate_dataframes(dfs: dict) -> tuple[list, bool]:
    """
    Quick function to validate DataFrames and return results.

    Args:
        dfs: Dictionary of DataFrames

    Returns:
        Tuple of (failures list, has_critical_failures bool)

    Usage:
        failures, has_critical = validate_dataframes(dfs)
        if has_critical:
            print("STOP! Fix critical issues before loading.")
    """
    validator = DataValidator()
    failures  = validator.validate_all(dfs)
    validator.save_failures(failures)
    return failures, validator.has_critical_failures()


# ─────────────────────────────────────────────────────────────────────────────
# QUICK TEST — run this file directly
# python src/etl/validator.py
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing DataValidator with sample data...")
    print("=" * 60)

    # Create sample DataFrames that have some issues
    companies_df = pd.DataFrame({
        "id":           ["TCS", "INFY", "TCS"],   # TCS is duplicate!
        "company_name": ["Tata Consultancy", "Infosys", "TCS Duplicate"],
        "face_value":   [1, 5, 1],
    })

    pl_df = pd.DataFrame({
        "company_id":        ["TCS",     "INFY",    "HDFCBANK"],
        "year":              ["2023-03",  "2023-03", "2023-03"],
        "sales":             [225458,     146767,    0],        # HDFCBANK sales=0
        "operating_profit":  [48534,      30000,     0],
        "opm_percentage":    [21.5,       99.0,      0],        # INFY OPM wrong!
        "net_profit":        [34990,      24095,     0],
        "eps":               [95.3,       57.0,      0],
        "tax_percentage":    [25.0,       25.0,      25.0],
        "dividend_payout":   [45.0,       45.0,      45.0],
    })

    bs_df = pd.DataFrame({
        "company_id":        ["TCS",    "INFY"],
        "year":              ["2023-03", "2023-03"],
        "total_assets":      [100000,    80000],
        "total_liabilities": [102000,    80000],   # TCS off by 2%!
        "fixed_assets":      [5000,      3000],
    })

    cf_df = pd.DataFrame({
        "company_id":         ["TCS",    "INFY"],
        "year":               ["2023-03", "2023-03"],
        "operating_activity": [40000,     25000],
        "investing_activity": [-5000,     -3000],
        "financing_activity": [-10000,    -8000],
        "net_cash_flow":      [25500,     14000],  # TCS net cash wrong!
    })

    dfs = {
        "companies":     companies_df,
        "profitandloss": pl_df,
        "balancesheet":  bs_df,
        "cashflow":      cf_df,
    }

    failures, has_critical = validate_dataframes(dfs)

    print(f"\nTotal failures found: {len(failures)}")
    print(f"Has critical failures: {has_critical}")
    print()

    for f in failures:
        print(f)

    print()
    print("Check output/validation_failures.csv for full report")