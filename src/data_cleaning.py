"""Cleaning and feature engineering for the Superstore orders dataset.

`clean_orders` is the public entry point; the private helpers below each do
one job so they can be tested and reasoned about in isolation.
"""

from __future__ import annotations

import pandas as pd

from . import config


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Turn the raw export into an analysis-ready frame.

    Applies, in order: numeric coercion, date parsing, duplicate removal and
    derived-column creation. The input frame is not modified.

    Args:
        df: Raw frame as returned by ``data_loader.load_raw_data``.

    Returns:
        A cleaned copy with parsed dates, numeric measures and the derived
        columns declared in ``config``.
    """
    out = df.copy()
    out = _strip_text_columns(out)
    out = _coerce_numeric_columns(out)
    out = _parse_dates(out)
    out = _drop_duplicate_order_lines(out)
    out = add_derived_columns(out)
    return out.reset_index(drop=True)


def _strip_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Trim surrounding whitespace from every text column."""
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        df[col] = df[col].astype("string").str.strip()
    return df


def _coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert text-encoded measures to floats.

    `sales` arrives with thousands separators ("1,275") and `shipping_cost`
    with padding, so both parse as text on load.

    Results are cast to plain float64 rather than pandas' nullable numeric
    types: nullable dtypes propagate into every downstream aggregation and
    turn pivot tables into `object` columns that matplotlib cannot plot.
    """
    for col in config.TEXT_NUMERIC_COLUMNS:
        if col not in df.columns:
            continue
        cleaned = df[col].astype("string").str.replace(",", "", regex=False)
        df[col] = pd.to_numeric(cleaned, errors="coerce").astype("float64")
    return df


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse the day-first date columns into datetimes."""
    for col in config.DATE_COLUMNS:
        df[col] = pd.to_datetime(
            df[col], format=config.RAW_DATE_FORMAT, errors="coerce"
        )
    return df


def _drop_duplicate_order_lines(df: pd.DataFrame) -> pd.DataFrame:
    """Remove repeated product lines within the same order.

    The same product may legitimately appear once per order only; repeats are
    export artefacts. The first occurrence is kept.
    """
    return df.drop_duplicates(subset=config.ORDER_LINE_KEY, keep="first")


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add the time, margin and grouping columns used across the analysis."""
    order_date = df[config.COL_ORDER_DATE]

    df[config.COL_YEAR] = order_date.dt.year
    df[config.COL_QUARTER] = order_date.dt.quarter
    df[config.COL_MONTH] = order_date.dt.month
    df[config.COL_MONTH_NAME] = pd.Categorical(
        order_date.dt.strftime("%b"), categories=config.MONTH_ORDER, ordered=True
    )
    # Month start as a timestamp keeps the column plottable on a time axis.
    df[config.COL_YEAR_MONTH] = order_date.dt.to_period("M").dt.to_timestamp()

    df[config.COL_PROFIT_MARGIN] = _safe_margin(
        df[config.COL_PROFIT], df[config.COL_SALES]
    )
    df[config.COL_IS_LOSS] = df[config.COL_PROFIT] < 0
    df[config.COL_SHIPPING_DAYS] = (
        df[config.COL_SHIP_DATE] - order_date
    ).dt.days

    df[config.COL_DISCOUNT_BAND] = pd.cut(
        df[config.COL_DISCOUNT],
        bins=config.DISCOUNT_BAND_EDGES,
        labels=config.DISCOUNT_BAND_LABELS,
        ordered=True,
    )
    df[config.COL_MARKET_REGION] = (
        df[config.COL_MARKET].astype("string")
        + config.MARKET_REGION_SEPARATOR
        + df[config.COL_REGION].astype("string")
    )
    return df


def _safe_margin(profit: pd.Series, sales: pd.Series) -> pd.Series:
    """Profit as a share of sales, guarding against zero-sales rows.

    A handful of rows have sales rounded down to 0; their margin is undefined
    rather than infinite.
    """
    return (profit / sales.where(sales > 0)).astype(float)
