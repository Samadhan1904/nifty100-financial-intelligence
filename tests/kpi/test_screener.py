"""
test_screener.py — Tests for the Screener Engine.

Run with:
    pytest tests/kpi/test_screener.py -v

Author: Samadhan
Sprint: 3 — Day 16
"""

import pytest
import pandas as pd
from src.analytics.screener.engine import ScreenerEngine


@pytest.fixture(scope="module")
def engine():
    """Create one ScreenerEngine for all tests."""
    return ScreenerEngine()


@pytest.fixture(scope="module")
def latest_df(engine):
    """Load latest ratios once for all tests."""
    from src.analytics.screener.engine import load_latest_ratios
    return load_latest_ratios()


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestScreenerConfig:

    def test_config_loads(self, engine):
        """Config must load without error."""
        assert engine.config is not None

    def test_all_presets_exist(self, engine):
        """All 6 presets must be in config."""
        presets = engine.get_available_presets()
        expected = [
            "quality_compounder",
            "value_pick",
            "growth_accelerator",
            "dividend_champion",
            "debt_free_blue_chip",
            "turnaround_watch",
        ]
        for p in expected:
            assert p in presets, f"Preset '{p}' missing from config"

    def test_preset_has_description(self, engine):
        """Each preset must have a description."""
        for preset in engine.get_available_presets():
            desc = engine.get_preset_description(preset)
            assert desc, f"Preset '{preset}' has no description"


# ─────────────────────────────────────────────────────────────────────────────
# FILTER TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestScreenerFilters:

    def test_roe_filter(self, engine):
        """ROE filter must return only companies above threshold."""
        results = engine.screen(min_roe=20)
        assert len(results) > 0
        assert all(
            results["return_on_equity_pct"] >= 20
        ), "Some companies have ROE < 20%"

    def test_de_filter(self, engine):
        """D/E filter must return only companies below threshold."""
        results = engine.screen(max_de=0.5)
        assert len(results) > 0
        assert all(
            results["debt_to_equity"] <= 0.5
        ), "Some companies have D/E > 0.5"

    def test_fcf_filter(self, engine):
        """FCF filter must return only positive FCF companies."""
        results = engine.screen(min_fcf=0)
        assert len(results) > 0
        assert all(
            results["free_cash_flow_cr"] >= 0
        ), "Some companies have negative FCF"

    def test_combined_filters(self, engine):
        """Combined filters must be more restrictive."""
        only_roe    = engine.screen(min_roe=15)
        roe_and_de  = engine.screen(min_roe=15, max_de=1.0)
        assert len(roe_and_de) <= len(only_roe), \
            "Adding D/E filter should not increase results"

    def test_sector_filter(self, engine):
        """Sector filter must only return companies from that sector."""
        results = engine.screen(sector="Information Technology")
        assert len(results) > 0
        assert all(
            results["broad_sector"] == "Information Technology"
        ), "Non-IT companies in IT filter results"

    def test_strict_filters_reduce_results(self, engine):
        """Very strict filters should return fewer results."""
        loose  = engine.screen(min_roe=10)
        strict = engine.screen(min_roe=50)
        assert len(strict) <= len(loose), \
            "Stricter ROE should return fewer or equal results"

    def test_no_filter_returns_all(self, engine):
        """No filters should return all 91 companies."""
        results = engine.screen()
        assert len(results) >= 88, \
            f"Expected ~91 companies, got {len(results)}"

    def test_impossible_filter_returns_empty(self, engine):
        """Impossible filter should return empty DataFrame."""
        results = engine.screen(min_roe=99999)
        assert len(results) == 0, \
            "Expected 0 results for impossible filter"


# ─────────────────────────────────────────────────────────────────────────────
# PRESET TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestPresets:

    def test_quality_compounder_returns_results(self, engine):
        """Quality compounder must find at least 10 companies."""
        results = engine.screen_from_config("quality_compounder")
        assert len(results) >= 10, \
            f"Quality compounder found only {len(results)} companies"

    def test_quality_compounder_has_tcs(self, engine):
        """TCS should be in quality compounder results."""
        results = engine.screen_from_config("quality_compounder")
        assert "TCS" in results["company_id"].values, \
            "TCS should pass quality compounder screen"

    def test_growth_accelerator_returns_results(self, engine):
        """Growth accelerator must find at least 5 companies."""
        results = engine.screen_from_config("growth_accelerator")
        assert len(results) >= 5, \
            f"Growth accelerator found only {len(results)} companies"

    def test_debt_free_has_low_de(self, engine):
        """Debt-free preset must only return low D/E companies."""
        results = engine.screen_from_config("debt_free_blue_chip")
        assert len(results) > 0
        assert all(
            results["debt_to_equity"] <= 0.1
        ), "Debt-free preset returned high D/E companies"

    def test_invalid_preset_raises_error(self, engine):
        """Invalid preset name must raise KeyError."""
        with pytest.raises(KeyError):
            engine.screen_from_config("nonexistent_preset")

    def test_all_presets_run_without_error(self, engine):
        """All 6 presets must run without raising exceptions."""
        for preset in engine.get_available_presets():
            try:
                results = engine.screen_from_config(preset)
                assert isinstance(results, pd.DataFrame)
            except Exception as e:
                pytest.fail(
                    f"Preset '{preset}' raised {type(e).__name__}: {e}"
                )

    def test_all_presets_return_dataframe(self, engine):
        """All presets must return a pandas DataFrame."""
        for preset in engine.get_available_presets():
            results = engine.screen_from_config(preset)
            assert isinstance(results, pd.DataFrame), \
                f"Preset '{preset}' did not return DataFrame"

    def test_results_have_required_columns(self, engine):
        """Results must contain key columns."""
        results = engine.screen_from_config("quality_compounder")
        required_cols = [
            "company_id",
            "company_name",
            "return_on_equity_pct",
            "debt_to_equity",
        ]
        for col in required_cols:
            assert col in results.columns, \
                f"Missing column '{col}' in screener results"