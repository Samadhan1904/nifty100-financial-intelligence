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

# ─────────────────────────────────────────────────────────────────────────────
# CAGR TESTS
# ─────────────────────────────────────────────────────────────────────────────

from src.analytics.cagr import compute_cagr, CAGRFlag


class TestCAGR:
    """Tests for compute_cagr() function."""

    def test_cagr_normal_10yr(self):
        """Standard 10 year CAGR"""
        val, flag = compute_cagr(100000, 240000, 10)
        assert val == pytest.approx(9.15, abs=0.1)
        assert flag == CAGRFlag.NORMAL

    def test_cagr_normal_5yr(self):
        """Standard 5 year CAGR"""
        val, flag = compute_cagr(50000, 100000, 5)
        assert val == pytest.approx(14.87, abs=0.1)
        assert flag == CAGRFlag.NORMAL

    def test_cagr_normal_3yr(self):
        """Standard 3 year CAGR"""
        val, flag = compute_cagr(80000, 100000, 3)
        assert val == pytest.approx(7.72, abs=0.1)
        assert flag == CAGRFlag.NORMAL

    def test_cagr_turnaround(self):
        """Base negative end positive — TURNAROUND"""
        val, flag = compute_cagr(-5000, 8000, 5)
        assert val is None
        assert flag == CAGRFlag.TURNAROUND

    def test_cagr_decline_to_loss(self):
        """Base positive end negative — DECLINE_TO_LOSS"""
        val, flag = compute_cagr(5000, -3000, 5)
        assert val is None
        assert flag == CAGRFlag.DECLINE_TO_LOSS

    def test_cagr_both_negative(self):
        """Both negative — BOTH_NEGATIVE"""
        val, flag = compute_cagr(-5000, -3000, 5)
        assert val is None
        assert flag == CAGRFlag.BOTH_NEGATIVE

    def test_cagr_zero_base(self):
        """Zero base — ZERO_BASE"""
        val, flag = compute_cagr(0, 50000, 5)
        assert val is None
        assert flag == CAGRFlag.ZERO_BASE

    def test_cagr_none_start(self):
        """None start — MISSING_DATA"""
        val, flag = compute_cagr(None, 50000, 5)
        assert val is None
        assert flag == CAGRFlag.MISSING_DATA

    def test_cagr_none_end(self):
        """None end — MISSING_DATA"""
        val, flag = compute_cagr(50000, None, 5)
        assert val is None
        assert flag == CAGRFlag.MISSING_DATA

    def test_cagr_insufficient_years(self):
        """n_years < 1 — INSUFFICIENT"""
        val, flag = compute_cagr(50000, 100000, 0)
        assert val is None
        assert flag == CAGRFlag.INSUFFICIENT

    def test_cagr_flat_growth(self):
        """No growth — 0% CAGR"""
        val, flag = compute_cagr(100000, 100000, 5)
        assert val == pytest.approx(0.0, abs=0.01)
        assert flag == CAGRFlag.NORMAL

    def test_cagr_negative_growth(self):
        """Declining revenue — negative CAGR"""
        val, flag = compute_cagr(100000, 50000, 5)
        assert val == pytest.approx(-12.94, abs=0.1)
        assert flag == CAGRFlag.NORMAL

    def test_cagr_one_year(self):
        """Single year growth"""
        val, flag = compute_cagr(100000, 115000, 1)
        assert val == pytest.approx(15.0, abs=0.1)
        assert flag == CAGRFlag.NORMAL

        # ─────────────────────────────────────────────────────────────────────────────
# CASH FLOW KPI TESTS
# ─────────────────────────────────────────────────────────────────────────────

from src.analytics.cashflow_kpis import (
    compute_fcf,
    compute_cfo_quality,
    compute_capex_intensity,
    compute_fcf_conversion,
    compute_capital_allocation_pattern,
    detect_distress,
    get_cfo_quality_tier,
    get_capex_tier,
    CapitalPattern,
)


class TestFCF:
    """Tests for compute_fcf()"""

    def test_fcf_positive(self):
        """Healthy FCF — CFO > |CFI|"""
        assert compute_fcf(40000, -5000) == 35000

    def test_fcf_negative(self):
        """Negative FCF — investing heavily"""
        assert compute_fcf(5000, -20000) == -15000

    def test_fcf_both_positive(self):
        """Both positive — selling assets"""
        assert compute_fcf(10000, 5000) == 15000

    def test_fcf_none_cfo(self):
        """None CFO — return None"""
        assert compute_fcf(None, -5000) is None

    def test_fcf_none_cfi(self):
        """None CFI — return None"""
        assert compute_fcf(40000, None) is None

    def test_fcf_zero_cfi(self):
        """Zero CFI — FCF equals CFO"""
        assert compute_fcf(40000, 0) == 40000


class TestCFOQuality:
    """Tests for compute_cfo_quality()"""

    def test_high_quality(self):
        """CFO > PAT — high quality"""
        result = compute_cfo_quality(40000, 35000)
        assert result == pytest.approx(1.14, abs=0.01)

    def test_accrual_risk(self):
        """CFO << PAT — accrual risk"""
        result = compute_cfo_quality(5000, 35000)
        assert result == pytest.approx(0.14, abs=0.01)

    def test_zero_profit(self):
        """Zero PAT — return None"""
        assert compute_cfo_quality(40000, 0) is None

    def test_negative_profit(self):
        """Negative PAT — return None"""
        assert compute_cfo_quality(40000, -5000) is None

    def test_none_cfo(self):
        """None CFO — return None"""
        assert compute_cfo_quality(None, 35000) is None

    def test_quality_tier_high(self):
        """High quality tier"""
        assert get_cfo_quality_tier(1.2) == "High Quality Earnings"

    def test_quality_tier_acceptable(self):
        """Acceptable tier"""
        assert get_cfo_quality_tier(0.7) == "Acceptable"

    def test_quality_tier_accrual(self):
        """Accrual risk tier"""
        assert get_cfo_quality_tier(0.3) == "Accrual Risk"

    def test_quality_tier_none(self):
        """None returns N/A"""
        assert get_cfo_quality_tier(None) == "N/A"


class TestCapexIntensity:
    """Tests for compute_capex_intensity()"""

    def test_asset_light(self):
        """IT company — asset light"""
        result = compute_capex_intensity(-5000, 225000)
        assert result == pytest.approx(2.22, abs=0.1)

    def test_capital_intensive(self):
        """Steel company — capital intensive"""
        result = compute_capex_intensity(-30000, 150000)
        assert result == pytest.approx(20.0, abs=0.1)

    def test_positive_cfi(self):
        """Positive CFI — selling assets, abs value used"""
        result = compute_capex_intensity(5000, 100000)
        assert result == pytest.approx(5.0, abs=0.1)

    def test_zero_sales(self):
        """Zero sales — return None"""
        assert compute_capex_intensity(-5000, 0) is None

    def test_none_cfi(self):
        """None CFI — return None"""
        assert compute_capex_intensity(None, 100000) is None

    def test_capex_tier_asset_light(self):
        """Asset light tier"""
        assert get_capex_tier(2.0) == "Asset-Light"

    def test_capex_tier_moderate(self):
        """Moderate tier"""
        assert get_capex_tier(5.0) == "Moderate"

    def test_capex_tier_intensive(self):
        """Capital intensive tier"""
        assert get_capex_tier(15.0) == "Capital Intensive"


class TestFCFConversion:
    """Tests for compute_fcf_conversion()"""

    def test_good_conversion(self):
        """70% conversion — efficient"""
        result = compute_fcf_conversion(35000, 50000)
        assert result == pytest.approx(70.0, abs=0.1)

    def test_negative_fcf(self):
        """Negative FCF — negative conversion"""
        result = compute_fcf_conversion(-5000, 50000)
        assert result == pytest.approx(-10.0, abs=0.1)

    def test_zero_ebitda(self):
        """Zero EBITDA — return None"""
        assert compute_fcf_conversion(35000, 0) is None

    def test_negative_ebitda(self):
        """Negative EBITDA — return None"""
        assert compute_fcf_conversion(35000, -10000) is None

    def test_none_fcf(self):
        """None FCF — return None"""
        assert compute_fcf_conversion(None, 50000) is None


class TestCapitalPattern:
    """Tests for compute_capital_allocation_pattern()"""

    def test_reinvestor(self):
        """+ - - pattern = Reinvestor"""
        result = compute_capital_allocation_pattern(40000, -5000, -10000)
        assert result == CapitalPattern.REINVESTOR

    def test_growth_financed(self):
        """+ - + pattern = Growth Financed"""
        result = compute_capital_allocation_pattern(40000, -5000, 10000)
        assert result == CapitalPattern.GROWTH_FINANCED

    def test_shareholder_returns(self):
        """+ + - pattern = Shareholder Returns"""
        result = compute_capital_allocation_pattern(40000, 5000, -10000)
        assert result == CapitalPattern.SHAREHOLDER_RETURN

    def test_distress_signal(self):
        """- - + pattern = Distress Signal"""
        result = compute_capital_allocation_pattern(-5000, -3000, 10000)
        assert result == CapitalPattern.DISTRESS

    def test_cash_burn(self):
        """- + + pattern = Cash Burn"""
        result = compute_capital_allocation_pattern(-5000, 5000, 10000)
        assert result == CapitalPattern.CASH_BURN


class TestDistressDetection:
    """Tests for detect_distress()"""

    def test_distress_detected(self):
        """CFO < 0 and CFF > 0 = distress"""
        assert detect_distress(-5000, 10000) is True

    def test_no_distress_positive_cfo(self):
        """CFO > 0 = no distress"""
        assert detect_distress(40000, 10000) is False

    def test_no_distress_negative_cff(self):
        """CFF < 0 = no distress"""
        assert detect_distress(-5000, -10000) is False

    def test_none_values(self):
        """None values = no distress"""
        assert detect_distress(None, 10000) is False