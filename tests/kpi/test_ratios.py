"""
test_ratios.py — Unit tests for financial ratio functions.

Run with:
    pytest tests/kpi/test_ratios.py -v

Author: Samadhan
Sprint: 2 — Day 8
"""

import pytest
from src.analytics.ratios import (
    compute_npm,
    compute_opm,
    compute_ebit_margin,
    compute_roe,
    compute_roce,
    compute_roa,
    compute_de_ratio,
    compute_icr,
    compute_asset_turnover,
    compute_net_debt,
)


# ─────────────────────────────────────────────────────────────────────────────
# NPM TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestNPM:

    def test_npm_normal(self):
        """TCS FY23 approximate values"""
        result = compute_npm(34990, 225458)
        assert result == pytest.approx(15.52, abs=0.1)

    def test_npm_negative_profit(self):
        """Loss-making company — negative NPM allowed"""
        result = compute_npm(-5000, 100000)
        assert result == pytest.approx(-5.0, abs=0.1)

    def test_npm_zero_sales(self):
        """Zero sales — return None"""
        assert compute_npm(1000, 0) is None

    def test_npm_none_profit(self):
        """None profit — return None"""
        assert compute_npm(None, 100000) is None

    def test_npm_none_sales(self):
        """None sales — return None"""
        assert compute_npm(10000, None) is None

    def test_npm_both_none(self):
        """Both None — return None"""
        assert compute_npm(None, None) is None


# ─────────────────────────────────────────────────────────────────────────────
# OPM TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestOPM:

    def test_opm_normal(self):
        """TCS FY23 approximate"""
        result = compute_opm(48534, 225458)
        assert result == pytest.approx(21.53, abs=0.1)

    def test_opm_zero_sales(self):
        assert compute_opm(10000, 0) is None

    def test_opm_none(self):
        assert compute_opm(None, 100000) is None


# ─────────────────────────────────────────────────────────────────────────────
# ROE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestROE:

    def test_roe_positive_equity(self):
        """Normal case — profit with positive equity"""
        result = compute_roe(10000, 1000, 49000)
        assert result == pytest.approx(20.0, abs=0.1)

    def test_roe_negative_equity(self):
        """Negative equity — return None"""
        result = compute_roe(10000, 1000, -5000)
        assert result is None

    def test_roe_zero_equity(self):
        """Zero equity — return None"""
        result = compute_roe(10000, 0, 0)
        assert result is None

    def test_roe_none_profit(self):
        """None profit — return None"""
        assert compute_roe(None, 1000, 49000) is None

    def test_roe_negative_profit(self):
        """Loss making — negative ROE"""
        result = compute_roe(-5000, 1000, 49000)
        assert result == pytest.approx(-10.0, abs=0.1)

    def test_roe_none_equity(self):
        """None equity fields — return None"""
        assert compute_roe(10000, None, None) is None


# ─────────────────────────────────────────────────────────────────────────────
# ROCE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestROCE:

    def test_roce_debt_free(self):
        """Debt-free company"""
        result = compute_roce(20000, 2000, 1000, 49000, 0)
        # EBIT = 18000, Capital = 50000, ROCE = 36%
        assert result == pytest.approx(36.0, abs=0.1)

    def test_roce_with_debt(self):
        """Company with debt"""
        result = compute_roce(20000, 2000, 1000, 49000, 10000)
        # EBIT = 18000, Capital = 60000, ROCE = 30%
        assert result == pytest.approx(30.0, abs=0.1)

    def test_roce_zero_capital(self):
        """Zero capital employed — return None"""
        assert compute_roce(10000, 0, 0, 0, 0) is None

    def test_roce_none_op_profit(self):
        """None operating profit — return None"""
        assert compute_roce(None, 1000, 1000, 49000, 0) is None


# ─────────────────────────────────────────────────────────────────────────────
# D/E RATIO TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestDERatio:

    def test_de_debt_free(self):
        """Zero borrowings — D/E = 0"""
        assert compute_de_ratio(0, 1000, 49000) == 0.0

    def test_de_normal(self):
        """Normal D/E calculation"""
        result = compute_de_ratio(10000, 1000, 49000)
        assert result == pytest.approx(0.2, abs=0.01)

    def test_de_high_leverage(self):
        """High leverage company"""
        result = compute_de_ratio(100000, 1000, 49000)
        assert result == pytest.approx(2.0, abs=0.01)

    def test_de_zero_equity(self):
        """Zero equity — return None"""
        assert compute_de_ratio(10000, 0, 0) is None

    def test_de_none_borrowings(self):
        """None borrowings — treat as 0, return 0.0"""
        assert compute_de_ratio(None, 1000, 49000) == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# ICR TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestICR:

    def test_icr_debt_free(self):
        """Zero interest — return None (Debt Free)"""
        assert compute_icr(10000, 500, 0) is None

    def test_icr_normal(self):
        """Normal ICR calculation"""
        result = compute_icr(10000, 500, 2000)
        assert result == pytest.approx(5.25, abs=0.01)

    def test_icr_none_interest(self):
        """None interest — return None"""
        assert compute_icr(10000, 500, None) is None

    def test_icr_strong(self):
        """Very strong coverage"""
        result = compute_icr(50000, 5000, 1000)
        assert result == pytest.approx(55.0, abs=0.1)


# ─────────────────────────────────────────────────────────────────────────────
# ASSET TURNOVER TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestAssetTurnover:

    def test_asset_turnover_normal(self):
        """Normal asset turnover"""
        result = compute_asset_turnover(200000, 100000)
        assert result == pytest.approx(2.0, abs=0.01)

    def test_asset_turnover_zero_assets(self):
        """Zero assets — return None"""
        assert compute_asset_turnover(100000, 0) is None

    def test_asset_turnover_none(self):
        """None values — return None"""
        assert compute_asset_turnover(None, 100000) is None


# ─────────────────────────────────────────────────────────────────────────────
# NET DEBT TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestNetDebt:

    def test_net_debt_positive(self):
        """More debt than investments"""
        result = compute_net_debt(10000, 2000)
        assert result == pytest.approx(8000.0, abs=0.1)

    def test_net_debt_negative(self):
        """Net cash positive"""
        result = compute_net_debt(5000, 10000)
        assert result == pytest.approx(-5000.0, abs=0.1)

    def test_net_debt_no_investments(self):
        """None investments — treat as 0"""
        result = compute_net_debt(10000, None)
        assert result == pytest.approx(10000.0, abs=0.1)

    def test_net_debt_zero_borrowings(self):
        """Zero borrowings"""
        result = compute_net_debt(0, 5000)
        assert result == pytest.approx(-5000.0, abs=0.1)