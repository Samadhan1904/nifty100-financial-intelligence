"""
Tests for all 16 DQ validation rules.

Run with:
    pytest tests/dq/test_rules.py -v

Author: Samadhan
Sprint: 1 — Day 3
"""

import pytest
import pandas as pd
from src.etl.validator import DataValidator, validate_dataframes


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — builds minimal valid DataFrames for testing
# ─────────────────────────────────────────────────────────────────────────────

def make_companies(ids=None):
    ids = ids or ["TCS", "INFY", "HDFCBANK"]
    return pd.DataFrame({
        "id":           ids,
        "company_name": [f"Company {i}" for i in ids],
        "face_value":   [1] * len(ids),
    })


def make_pl(company_ids=None):
    company_ids = company_ids or ["TCS", "INFY"]
    return pd.DataFrame({
        "company_id":       company_ids,
        "year":             ["2023-03"] * len(company_ids),
        "sales":            [100000] * len(company_ids),
        "operating_profit": [20000]  * len(company_ids),
        "opm_percentage":   [20.0]   * len(company_ids),
        "net_profit":       [15000]  * len(company_ids),
        "eps":              [50.0]   * len(company_ids),
        "tax_percentage":   [25.0]   * len(company_ids),
        "dividend_payout":  [40.0]   * len(company_ids),
    })


def make_bs(company_ids=None):
    company_ids = company_ids or ["TCS", "INFY"]
    return pd.DataFrame({
        "company_id":        company_ids,
        "year":              ["2023-03"] * len(company_ids),
        "total_assets":      [100000]    * len(company_ids),
        "total_liabilities": [100000]    * len(company_ids),
        "fixed_assets":      [5000]      * len(company_ids),
    })


def make_cf(company_ids=None):
    company_ids = company_ids or ["TCS", "INFY"]
    return pd.DataFrame({
        "company_id":         company_ids,
        "year":               ["2023-03"] * len(company_ids),
        "operating_activity": [20000]     * len(company_ids),
        "investing_activity": [-5000]     * len(company_ids),
        "financing_activity": [-10000]    * len(company_ids),
        "net_cash_flow":      [5000]      * len(company_ids),
    })


# ─────────────────────────────────────────────────────────────────────────────
# DQ-01 TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestDQ01CompanyPKUniqueness:

    def test_dq01_passes_when_all_unique(self):
        """No duplicate IDs — should pass"""
        v = DataValidator()
        v._dq01_company_pk_uniqueness(make_companies(["TCS", "INFY", "HDFCBANK"]))
        dq01 = [f for f in v.failures if f.rule_id == "DQ-01"]
        assert len(dq01) == 0

    def test_dq01_fails_when_duplicate(self):
        """Duplicate TCS — should trigger CRITICAL"""
        v = DataValidator()
        v._dq01_company_pk_uniqueness(make_companies(["TCS", "TCS", "INFY"]))
        dq01 = [f for f in v.failures if f.rule_id == "DQ-01"]
        assert len(dq01) == 1
        assert dq01[0].severity == "CRITICAL"

    def test_dq01_empty_df_no_crash(self):
        """Empty DataFrame should not crash"""
        v = DataValidator()
        v._dq01_company_pk_uniqueness(pd.DataFrame())
        assert len(v.failures) == 0


# ─────────────────────────────────────────────────────────────────────────────
# DQ-02 TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestDQ02AnnualPKUniqueness:

    def test_dq02_passes_when_unique(self):
        """Unique (company_id, year) pairs — should pass"""
        v = DataValidator()
        df = make_pl(["TCS", "INFY"])
        v._dq02_annual_pk_uniqueness(df, pd.DataFrame(), pd.DataFrame())
        dq02 = [f for f in v.failures if f.rule_id == "DQ-02"]
        assert len(dq02) == 0

    def test_dq02_fails_when_duplicate_row(self):
        """Duplicate (TCS, 2023-03) — should trigger CRITICAL"""
        v = DataValidator()
        df = pd.DataFrame({
            "company_id": ["TCS", "TCS", "INFY"],
            "year":       ["2023-03", "2023-03", "2023-03"],
            "sales":      [100, 100, 200],
        })
        v._dq02_annual_pk_uniqueness(df, pd.DataFrame(), pd.DataFrame())
        dq02 = [f for f in v.failures if f.rule_id == "DQ-02"]
        assert len(dq02) == 1
        assert dq02[0].severity == "CRITICAL"


# ─────────────────────────────────────────────────────────────────────────────
# DQ-03 TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestDQ03FKIntegrity:

    def test_dq03_passes_when_all_ids_valid(self):
        """All company_ids exist in companies — should pass"""
        v = DataValidator()
        v._dq03_fk_integrity(
            make_companies(["TCS", "INFY"]),
            make_pl(["TCS", "INFY"]),
            pd.DataFrame(),
            pd.DataFrame(),
        )
        dq03 = [f for f in v.failures if f.rule_id == "DQ-03"]
        assert len(dq03) == 0

    def test_dq03_fails_when_orphan_id(self):
        """UNKNOWN not in companies — should trigger CRITICAL"""
        v = DataValidator()
        v._dq03_fk_integrity(
            make_companies(["TCS", "INFY"]),
            make_pl(["TCS", "UNKNOWN"]),
            pd.DataFrame(),
            pd.DataFrame(),
        )
        dq03 = [f for f in v.failures if f.rule_id == "DQ-03"]
        assert len(dq03) == 1
        assert dq03[0].severity == "CRITICAL"


# ─────────────────────────────────────────────────────────────────────────────
# DQ-04 TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestDQ04BalanceSheetBalance:

    def test_dq04_passes_when_balanced(self):
        """assets == liabilities — should pass"""
        v = DataValidator()
        v._dq04_balance_sheet_balance(make_bs())
        dq04 = [f for f in v.failures if f.rule_id == "DQ-04"]
        assert len(dq04) == 0

    def test_dq04_fails_when_unbalanced(self):
        """assets != liabilities by more than 1% — should trigger WARNING"""
        v = DataValidator()
        bs = pd.DataFrame({
            "company_id":        ["TCS"],
            "year":              ["2023-03"],
            "total_assets":      [1000],
            "total_liabilities": [1020],   # 2% diff
            "fixed_assets":      [500],
        })
        v._dq04_balance_sheet_balance(bs)
        dq04 = [f for f in v.failures if f.rule_id == "DQ-04"]
        assert len(dq04) == 1
        assert dq04[0].severity == "WARNING"

    def test_dq04_passes_within_tolerance(self):
        """assets vs liabilities within 1% — should pass"""
        v = DataValidator()
        bs = pd.DataFrame({
            "company_id":        ["TCS"],
            "year":              ["2023-03"],
            "total_assets":      [1000],
            "total_liabilities": [1005],   # 0.5% diff — within tolerance
            "fixed_assets":      [500],
        })
        v._dq04_balance_sheet_balance(bs)
        dq04 = [f for f in v.failures if f.rule_id == "DQ-04"]
        assert len(dq04) == 0


# ─────────────────────────────────────────────────────────────────────────────
# DQ-06 TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestDQ06PositiveSales:

    def test_dq06_passes_when_sales_positive(self):
        """Positive sales — should pass"""
        v = DataValidator()
        v._dq06_positive_sales(make_pl())
        dq06 = [f for f in v.failures if f.rule_id == "DQ-06"]
        assert len(dq06) == 0

    def test_dq06_fails_when_sales_zero(self):
        """Zero sales — should trigger WARNING"""
        v = DataValidator()
        df = pd.DataFrame({
            "company_id": ["TCS"],
            "year":       ["2023-03"],
            "sales":      [0],
        })
        v._dq06_positive_sales(df)
        dq06 = [f for f in v.failures if f.rule_id == "DQ-06"]
        assert len(dq06) == 1
        assert dq06[0].severity == "WARNING"

    def test_dq06_fails_when_sales_negative(self):
        """Negative sales — should trigger WARNING"""
        v = DataValidator()
        df = pd.DataFrame({
            "company_id": ["TCS"],
            "year":       ["2023-03"],
            "sales":      [-5000],
        })
        v._dq06_positive_sales(df)
        dq06 = [f for f in v.failures if f.rule_id == "DQ-06"]
        assert len(dq06) == 1


# ─────────────────────────────────────────────────────────────────────────────
# DQ-09 TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestDQ09NetCashCheck:

    def test_dq09_passes_when_cash_matches(self):
        """net_cash_flow matches CFO+CFI+CFF — should pass"""
        v = DataValidator()
        v._dq09_net_cash_check(make_cf())
        dq09 = [f for f in v.failures if f.rule_id == "DQ-09"]
        assert len(dq09) == 0

    def test_dq09_fails_when_cash_mismatch(self):
        """net_cash_flow differs by more than 10 Cr — should trigger WARNING"""
        v = DataValidator()
        cf = pd.DataFrame({
            "company_id":         ["TCS"],
            "year":               ["2023-03"],
            "operating_activity": [20000],
            "investing_activity": [-5000],
            "financing_activity": [-10000],
            "net_cash_flow":      [10000],  # should be 5000, diff = 5000
        })
        v._dq09_net_cash_check(cf)
        dq09 = [f for f in v.failures if f.rule_id == "DQ-09"]
        assert len(dq09) == 1
        assert dq09[0].severity == "WARNING"


# ─────────────────────────────────────────────────────────────────────────────
# DQ-11 TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestDQ11TaxRateRange:

    def test_dq11_passes_normal_tax(self):
        """Normal tax rate 25% — should pass"""
        v = DataValidator()
        v._dq11_tax_rate_range(make_pl())
        dq11 = [f for f in v.failures if f.rule_id == "DQ-11"]
        assert len(dq11) == 0

    def test_dq11_fails_when_tax_too_high(self):
        """Tax > 60% — should trigger WARNING"""
        v = DataValidator()
        df = pd.DataFrame({
            "company_id":     ["TCS"],
            "year":           ["2023-03"],
            "tax_percentage": [75.0],
        })
        v._dq11_tax_rate_range(df)
        dq11 = [f for f in v.failures if f.rule_id == "DQ-11"]
        assert len(dq11) == 1
        assert dq11[0].severity == "WARNING"

    def test_dq11_fails_when_tax_negative(self):
        """Negative tax — should trigger WARNING"""
        v = DataValidator()
        df = pd.DataFrame({
            "company_id":     ["TCS"],
            "year":           ["2023-03"],
            "tax_percentage": [-5.0],
        })
        v._dq11_tax_rate_range(df)
        dq11 = [f for f in v.failures if f.rule_id == "DQ-11"]
        assert len(dq11) == 1


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRATION TEST
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateAll:

    def test_clean_data_has_no_critical_failures(self):
        """Perfectly clean data should have no critical failures"""
        dfs = {
            "companies":     make_companies(["TCS", "INFY"]),
            "profitandloss": make_pl(["TCS", "INFY"]),
            "balancesheet":  make_bs(["TCS", "INFY"]),
            "cashflow":      make_cf(["TCS", "INFY"]),
        }
        failures, has_critical = validate_dataframes(dfs)
        assert not has_critical, (
            f"Expected no critical failures but got: "
            f"{[f for f in failures if f.severity == 'CRITICAL']}"
        )

    def test_duplicate_company_causes_critical(self):
        """Duplicate company ID must cause critical failure"""
        dfs = {
            "companies": make_companies(["TCS", "TCS", "INFY"]),
        }
        failures, has_critical = validate_dataframes(dfs)
        assert has_critical

    def test_orphan_fk_causes_critical(self):
        """Orphan foreign key must cause critical failure"""
        dfs = {
            "companies":     make_companies(["TCS"]),
            "profitandloss": make_pl(["TCS", "UNKNOWN"]),
        }
        failures, has_critical = validate_dataframes(dfs)
        assert has_critical