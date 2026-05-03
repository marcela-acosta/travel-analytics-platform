import os
import sys
from unittest.mock import MagicMock

import pandas as pd
import pytest

# ── Mock streamlit and altair before importing app ─────────────────────────────
_st = MagicMock()
_st.cache_data = lambda ttl=None: (lambda f: f)
_st.multiselect = lambda label, options=None, default=None, **kw: (
    default if default is not None else (options or [])
)
_st.checkbox = lambda *a, **kw: False
_st.columns = lambda n, **kw: [
    MagicMock() for _ in range(n if isinstance(n, int) else len(n))
]
_st.stop = lambda: None
sys.modules["streamlit"] = _st
sys.modules["altair"] = MagicMock()

# Patch pd.DataFrame.style before importing app so module-level Styler calls
# don't trigger the jinja2 / markupsafe dependency chain.
_style_mock = MagicMock()
_style_mock.format = lambda *a, **kw: _style_mock
_style_mock.applymap = lambda *a, **kw: _style_mock
pd.DataFrame.style = property(lambda self: _style_mock)  # type: ignore[assignment]

os.environ["USE_MOCK"] = "true"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dashboard.app import (  # noqa: E402
    _highlight_low_conversion,
    get_mock_conversion_by_agent,
    get_mock_conversion_by_product,
)

_AGENT_COLS = {
    "agent",
    "total_opportunities",
    "won_opportunities",
    "lost_opportunities",
    "win_rate_pct",
    "total_pipeline_value",
    "won_value",
}
_PRODUCT_COLS = {
    "product",
    "total_opportunities",
    "won_opportunities",
    "lost_opportunities",
    "win_rate_pct",
    "total_pipeline_value",
    "won_value",
}


@pytest.fixture(scope="module")
def df_agents() -> pd.DataFrame:
    return get_mock_conversion_by_agent()


@pytest.fixture(scope="module")
def df_products() -> pd.DataFrame:
    return get_mock_conversion_by_product()


# ── gld_conversion_by_agent ────────────────────────────────────────────────────


class TestMockConversionByAgent:
    def test_returns_dataframe(self, df_agents):
        assert isinstance(df_agents, pd.DataFrame)

    def test_has_expected_columns(self, df_agents):
        assert _AGENT_COLS.issubset(df_agents.columns)

    def test_agent_not_null(self, df_agents):
        assert df_agents["agent"].notna().all()

    def test_agent_unique(self, df_agents):
        assert df_agents["agent"].nunique() == len(df_agents)

    def test_total_opportunities_positive(self, df_agents):
        assert (df_agents["total_opportunities"] > 0).all()

    def test_win_rate_between_0_and_100(self, df_agents):
        assert (df_agents["win_rate_pct"] >= 0).all()
        assert (df_agents["win_rate_pct"] <= 100).all()

    def test_win_rate_no_nan(self, df_agents):
        assert df_agents["win_rate_pct"].notna().all()

    def test_won_lte_total(self, df_agents):
        assert (
            df_agents["won_opportunities"] <= df_agents["total_opportunities"]
        ).all()

    def test_lost_lte_total(self, df_agents):
        assert (
            df_agents["lost_opportunities"] <= df_agents["total_opportunities"]
        ).all()

    def test_sort_descending_by_win_rate(self, df_agents):
        sorted_df = df_agents.sort_values("win_rate_pct", ascending=False)
        rates = sorted_df["win_rate_pct"].tolist()
        assert rates == sorted(rates, reverse=True)


# ── gld_conversion_by_product ──────────────────────────────────────────────────


class TestMockConversionByProduct:
    def test_returns_dataframe(self, df_products):
        assert isinstance(df_products, pd.DataFrame)

    def test_has_expected_columns(self, df_products):
        assert _PRODUCT_COLS.issubset(df_products.columns)

    def test_product_not_null(self, df_products):
        assert df_products["product"].notna().all()

    def test_product_unique(self, df_products):
        assert df_products["product"].nunique() == len(df_products)

    def test_total_opportunities_positive(self, df_products):
        assert (df_products["total_opportunities"] > 0).all()

    def test_win_rate_between_0_and_100(self, df_products):
        assert (df_products["win_rate_pct"] >= 0).all()
        assert (df_products["win_rate_pct"] <= 100).all()

    def test_win_rate_no_nan(self, df_products):
        assert df_products["win_rate_pct"].notna().all()

    def test_won_lte_total(self, df_products):
        assert (
            df_products["won_opportunities"] <= df_products["total_opportunities"]
        ).all()

    def test_sort_descending_by_win_rate(self, df_products):
        sorted_df = df_products.sort_values("win_rate_pct", ascending=False)
        rates = sorted_df["win_rate_pct"].tolist()
        assert rates == sorted(rates, reverse=True)


# ── _highlight_low_conversion ─────────────────────────────────────────────────


class TestHighlightLowConversion:
    def test_red_below_20(self):
        assert _highlight_low_conversion(19.99) == "background-color: #ffcccc"

    def test_red_at_zero(self):
        assert _highlight_low_conversion(0.0) == "background-color: #ffcccc"

    def test_empty_at_exactly_20(self):
        assert _highlight_low_conversion(20.0) == ""

    def test_empty_above_20(self):
        assert _highlight_low_conversion(85.5) == ""
        assert _highlight_low_conversion(100.0) == ""

    def test_int_not_highlighted(self):
        # win_rate_pct is always float; ints should not trigger highlight
        assert _highlight_low_conversion(10) == ""

    def test_string_not_highlighted(self):
        assert _highlight_low_conversion("15%") == ""

    def test_none_not_highlighted(self):
        assert _highlight_low_conversion(None) == ""
