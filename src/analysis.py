"""Aggregations answering the three business questions.

Every function takes a cleaned frame (see ``data_cleaning.clean_orders``) and
returns a new frame or scalar summary, so they compose freely and are shared
by both the notebook and the Streamlit app.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable, Sequence

import pandas as pd

from . import config

# Measures aggregated for any grouping dimension.
_BASE_AGGREGATION = {
    config.COL_SALES: "sum",
    config.COL_PROFIT: "sum",
    config.COL_QUANTITY: "sum",
    config.COL_DISCOUNT: "mean",
    config.COL_ORDER_ID: "nunique",
}

_AGGREGATION_RENAMES = {
    config.COL_SALES: "revenue",
    config.COL_PROFIT: "profit",
    config.COL_QUANTITY: "units",
    config.COL_DISCOUNT: "avg_discount",
    config.COL_ORDER_ID: "orders",
}


# --- Filtering -------------------------------------------------------------


def filter_orders(
    df: pd.DataFrame,
    date_range: tuple[date, date] | None = None,
    markets: Sequence[str] | None = None,
    regions: Sequence[str] | None = None,
    categories: Sequence[str] | None = None,
    segments: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Filter orders by date window and categorical dimensions.

    A ``None`` or empty selection means "no filter" for that dimension, which
    lets the Streamlit sidebar pass its widget values through unchanged.
    """
    mask = pd.Series(True, index=df.index)

    if date_range is not None:
        start, end = date_range
        order_date = df[config.COL_ORDER_DATE]
        mask &= order_date.between(pd.Timestamp(start), pd.Timestamp(end))

    for column, selection in (
        (config.COL_MARKET, markets),
        (config.COL_REGION, regions),
        (config.COL_CATEGORY, categories),
        (config.COL_SEGMENT, segments),
    ):
        if selection:
            mask &= df[column].isin(list(selection))

    return df[mask]


# --- Headline KPIs ---------------------------------------------------------


def calculate_kpis(df: pd.DataFrame) -> dict[str, float]:
    """Compute the headline metrics shown as dashboard KPI cards."""
    revenue = float(df[config.COL_SALES].sum())
    profit = float(df[config.COL_PROFIT].sum())
    return {
        "revenue": revenue,
        "profit": profit,
        "orders": int(df[config.COL_ORDER_ID].nunique()),
        "units": int(df[config.COL_QUANTITY].sum()),
        "avg_discount": float(df[config.COL_DISCOUNT].mean()) if len(df) else 0.0,
        "profit_margin": profit / revenue if revenue else 0.0,
        "loss_making_share": float(df[config.COL_IS_LOSS].mean()) if len(df) else 0.0,
    }


# --- Generic grouping ------------------------------------------------------


def summarise_by(
    df: pd.DataFrame,
    by: str | Iterable[str],
    sort_by: str = "revenue",
    top_n: int | None = None,
) -> pd.DataFrame:
    """Aggregate revenue, profit, units, orders and margin over a dimension.

    Args:
        df: Cleaned orders.
        by: Column name(s) to group on.
        sort_by: Output column to sort descending by.
        top_n: Keep only the highest ``top_n`` groups, if given.

    Returns:
        One row per group with a ``profit_margin`` column added.
    """
    grouped = (
        df.groupby(by, observed=True)
        .agg(_BASE_AGGREGATION)
        .rename(columns=_AGGREGATION_RENAMES)
        .reset_index()
    )
    grouped["profit_margin"] = _margin(grouped)
    grouped = grouped.sort_values(sort_by, ascending=False, ignore_index=True)
    return grouped.head(top_n) if top_n else grouped


def _margin(df: pd.DataFrame) -> pd.Series:
    """Profit margin from aggregated revenue and profit columns."""
    return (df["profit"] / df["revenue"].where(df["revenue"] > 0)).astype(float)


# --- Q1: regional and category performance ---------------------------------


def performance_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue and profit per market-qualified region.

    Uses ``market_region`` because raw region names repeat across markets.
    """
    return summarise_by(df, config.COL_MARKET_REGION)


def performance_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue and profit per product category."""
    return summarise_by(df, config.COL_CATEGORY)


def performance_by_sub_category(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue and profit per sub-category, with its parent category kept."""
    return summarise_by(df, [config.COL_CATEGORY, config.COL_SUB_CATEGORY])


def performance_by_country(df: pd.DataFrame, top_n: int | None = None) -> pd.DataFrame:
    """Revenue and profit per country, for the choropleth map."""
    return summarise_by(df, config.COL_COUNTRY, top_n=top_n)


# --- Q2: discount efficiency -----------------------------------------------


def discount_band_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Average margin and loss rate for each discount band.

    Shows where along the discount ladder profitability turns negative.
    """
    grouped = (
        df.groupby(config.COL_DISCOUNT_BAND, observed=True)
        .agg(
            revenue=(config.COL_SALES, "sum"),
            profit=(config.COL_PROFIT, "sum"),
            order_lines=(config.COL_SALES, "size"),
            loss_making_share=(config.COL_IS_LOSS, "mean"),
        )
        .reset_index()
    )
    grouped["profit_margin"] = _margin(grouped)
    return grouped


def discount_profit_correlation(df: pd.DataFrame) -> float:
    """Pearson correlation between discount rate and profit margin."""
    subset = df[[config.COL_DISCOUNT, config.COL_PROFIT_MARGIN]].dropna()
    return float(subset[config.COL_DISCOUNT].corr(subset[config.COL_PROFIT_MARGIN]))


def break_even_discount(df: pd.DataFrame) -> float | None:
    """Lowest discount band whose aggregate profit is negative.

    Returns the band's lower edge as a rate, or ``None`` if every band is
    profitable.
    """
    bands = discount_band_summary(df)
    losing = bands[bands["profit"] < 0]
    if losing.empty:
        return None
    first_losing_label = losing.iloc[0][config.COL_DISCOUNT_BAND]
    index = config.DISCOUNT_BAND_LABELS.index(first_losing_label)
    return config.DISCOUNT_BAND_EDGES[index]


def over_discounted_groups(
    df: pd.DataFrame,
    by: str | Iterable[str] = config.COL_SUB_CATEGORY,
    min_orders: int = config.MIN_ORDERS_FOR_RANKING,
    top_n: int = 10,
) -> pd.DataFrame:
    """Rank groups that lose money despite meaningful sales volume.

    Thin groups are excluded first so a single bad order cannot dominate the
    ranking. Only genuinely loss-making groups are returned, so the result may
    contain fewer than ``top_n`` rows (or none at all).
    """
    summary = summarise_by(df, by)
    material = summary[summary["orders"] >= min_orders]
    loss_making = material[material["profit"] < 0]
    return loss_making.nsmallest(top_n, "profit").reset_index(drop=True)


def discount_vs_margin_scatter(
    df: pd.DataFrame, by: str | Iterable[str] = config.COL_SUB_CATEGORY
) -> pd.DataFrame:
    """Per-group average discount against profit margin, sized by revenue."""
    return summarise_by(df, by, sort_by="revenue")


# --- Q3: trends and seasonality --------------------------------------------


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue and profit per calendar month across the whole period."""
    return summarise_by(
        df, config.COL_YEAR_MONTH, sort_by=config.COL_YEAR_MONTH
    ).sort_values(config.COL_YEAR_MONTH, ignore_index=True)


def yearly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue and profit per year, with year-on-year revenue growth."""
    yearly = summarise_by(df, config.COL_YEAR, sort_by=config.COL_YEAR)
    yearly = yearly.sort_values(config.COL_YEAR, ignore_index=True)
    yearly["revenue_growth"] = yearly["revenue"].pct_change()
    return yearly


def seasonality_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Average monthly revenue across years, to expose seasonal shape.

    Totals are divided by the number of years each month appears in so that a
    partial final year does not distort the profile.
    """
    monthly = monthly_trend(df)
    monthly[config.COL_MONTH_NAME] = pd.Categorical(
        monthly[config.COL_YEAR_MONTH].dt.strftime("%b"),
        categories=config.MONTH_ORDER,
        ordered=True,
    )
    seasonal = (
        monthly.groupby(config.COL_MONTH_NAME, observed=True)
        .agg(avg_revenue=("revenue", "mean"), avg_profit=("profit", "mean"))
        .reset_index()
    )
    return seasonal.sort_values(config.COL_MONTH_NAME, ignore_index=True)


def quarterly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue and profit per quarter of each year."""
    return summarise_by(
        df, [config.COL_YEAR, config.COL_QUARTER], sort_by=config.COL_YEAR
    ).sort_values([config.COL_YEAR, config.COL_QUARTER], ignore_index=True)
