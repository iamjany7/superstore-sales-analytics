"""Streamlit dashboard for the Superstore sales analytics project.

Run from the project root with:  streamlit run app/app.py

All data preparation and aggregation is imported from /src, so the dashboard
and the exploration notebook always report identical figures.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Make /src importable whether Streamlit is launched from the project root or
# from inside app/.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import analysis as an  # noqa: E402
from src import config  # noqa: E402
from src.data_loader import load_clean_data  # noqa: E402

# --- Page setup ------------------------------------------------------------

PAGE_TITLE = "Superstore Sales Analytics"
COLOR_REVENUE = "#2E5EAA"
COLOR_PROFIT = "#2A9D8F"
COLOR_LOSS = "#D1495B"
PROFIT_SCALE = [COLOR_LOSS, "#F4E4C1", COLOR_PROFIT]
CHART_HEIGHT = 380

st.set_page_config(page_title=PAGE_TITLE, page_icon="📊", layout="wide")


@st.cache_data(show_spinner="Loading Superstore data…")
def get_data() -> pd.DataFrame:
    """Load and clean the dataset once per session."""
    return load_clean_data()


# --- Formatting helpers ----------------------------------------------------


def format_currency(value: float) -> str:
    """Render a monetary value compactly ($1.2M / $340.5k / $912)."""
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:,.1f}k"
    return f"${value:,.0f}"


def format_percent(value: float) -> str:
    """Render a rate as a one-decimal percentage."""
    return f"{value:.1%}"


def to_percentage_points(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Scale ratio columns to percentage points for display.

    ``st.column_config.NumberColumn`` applies its printf format verbatim, so a
    ratio of 0.116 with "%.1f%%" would render as "0.1%". Scaling first is what
    makes the "%.1f%%" format correct.
    """
    display = df.copy()
    for column in columns:
        display[column] = display[column] * 100
    return display


# --- Sidebar ---------------------------------------------------------------


def render_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    """Draw the filter controls and return the filtered frame."""
    st.sidebar.header("Filters")

    min_date = df[config.COL_ORDER_DATE].min().date()
    max_date = df[config.COL_ORDER_DATE].max().date()
    date_range = st.sidebar.date_input(
        "Order date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    # While the user is mid-selection the widget returns a single date.
    if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
        date_range = (min_date, max_date)

    markets = st.sidebar.multiselect(
        "Market", sorted(df[config.COL_MARKET].dropna().unique())
    )
    # Offer only the regions that exist inside the chosen markets.
    region_pool = df[df[config.COL_MARKET].isin(markets)] if markets else df
    regions = st.sidebar.multiselect(
        "Region", sorted(region_pool[config.COL_REGION].dropna().unique())
    )
    categories = st.sidebar.multiselect(
        "Category", sorted(df[config.COL_CATEGORY].dropna().unique())
    )
    segments = st.sidebar.multiselect(
        "Customer segment", sorted(df[config.COL_SEGMENT].dropna().unique())
    )

    st.sidebar.caption(
        "Region names repeat across markets (EU, LATAM and US all have a "
        "“Central”), so charts group by market-qualified region."
    )
    st.sidebar.divider()
    st.sidebar.caption(f"[Dataset source]({config.DATASET_URL}) · Kaggle")

    return an.filter_orders(
        df,
        date_range=date_range,
        markets=markets,
        regions=regions,
        categories=categories,
        segments=segments,
    )


# --- Sections --------------------------------------------------------------


def render_kpis(df: pd.DataFrame) -> None:
    """Draw the headline KPI cards."""
    kpis = an.calculate_kpis(df)
    columns = st.columns(5)
    cards = [
        ("Total revenue", format_currency(kpis["revenue"]), None),
        ("Total profit", format_currency(kpis["profit"]),
         f"{format_percent(kpis['profit_margin'])} margin"),
        ("Orders", f"{kpis['orders']:,}", f"{kpis['units']:,} units"),
        ("Avg. discount", format_percent(kpis["avg_discount"]), None),
        ("Loss-making lines", format_percent(kpis["loss_making_share"]),
         "of all order lines"),
    ]
    for column, (label, value, caption) in zip(columns, cards):
        column.metric(label, value)
        if caption:
            column.caption(caption)


def render_performance_tab(df: pd.DataFrame) -> None:
    """Revenue and profit broken down by category, region and country."""
    left, right = st.columns(2)

    category = an.performance_by_category(df)
    fig = px.bar(
        category, x=config.COL_CATEGORY, y=["revenue", "profit"],
        barmode="group", title="Revenue vs profit by category",
        color_discrete_sequence=[COLOR_REVENUE, COLOR_PROFIT],
        labels={"value": "USD", "variable": ""},
    )
    fig.update_layout(height=CHART_HEIGHT, xaxis_title=None)
    left.plotly_chart(fig, width="stretch")

    region = an.performance_by_region(df).head(12).sort_values("revenue")
    fig = px.bar(
        region, x="revenue", y=config.COL_MARKET_REGION, orientation="h",
        color="profit_margin", color_continuous_scale=PROFIT_SCALE,
        color_continuous_midpoint=0,
        title="Top regions by revenue (shaded by profit margin)",
        labels={"revenue": "Revenue", config.COL_MARKET_REGION: "",
                "profit_margin": "Margin"},
    )
    fig.update_layout(height=CHART_HEIGHT)
    right.plotly_chart(fig, width="stretch")

    sub = an.performance_by_sub_category(df).sort_values("profit")
    fig = px.bar(
        sub, x="profit", y=config.COL_SUB_CATEGORY, orientation="h",
        color="profit", color_continuous_scale=PROFIT_SCALE,
        color_continuous_midpoint=0,
        title="Profit by sub-category",
        labels={"profit": "Profit", config.COL_SUB_CATEGORY: ""},
        hover_data={"revenue": ":,.0f", "profit_margin": ":.1%"},
    )
    fig.update_layout(height=520)
    st.plotly_chart(fig, width="stretch")

    country = an.performance_by_country(df)
    fig = px.choropleth(
        country, locations=config.COL_COUNTRY, locationmode="country names",
        color="profit", color_continuous_scale=PROFIT_SCALE,
        color_continuous_midpoint=0,
        title="Profit by country",
        hover_data={"revenue": ":,.0f", "orders": True},
    )
    fig.update_layout(height=460, margin={"l": 0, "r": 0, "t": 50, "b": 0})
    st.plotly_chart(fig, width="stretch")


def render_discount_tab(df: pd.DataFrame) -> None:
    """The discount-versus-margin story."""
    bands = an.discount_band_summary(df)
    correlation = an.discount_profit_correlation(df)
    break_even = an.break_even_discount(df)

    if break_even is not None:
        st.warning(
            f"Aggregate profit turns **negative from the {break_even:.0%} "
            f"discount band onward**. Correlation between discount rate and "
            f"profit margin: **{correlation:.2f}**."
        )
    else:
        st.success(
            f"Every discount band is profitable for this selection. "
            f"Discount/margin correlation: **{correlation:.2f}**."
        )

    left, right = st.columns(2)

    fig = px.bar(
        bands, x=config.COL_DISCOUNT_BAND, y="profit_margin",
        color="profit_margin", color_continuous_scale=PROFIT_SCALE,
        color_continuous_midpoint=0,
        title="Profit margin by discount band",
        labels={"profit_margin": "Margin", config.COL_DISCOUNT_BAND: "Discount"},
    )
    fig.update_layout(height=CHART_HEIGHT, yaxis_tickformat=".0%",
                      coloraxis_showscale=False)
    left.plotly_chart(fig, width="stretch")

    fig = px.bar(
        bands, x=config.COL_DISCOUNT_BAND, y="loss_making_share",
        title="Share of order lines sold at a loss",
        labels={"loss_making_share": "Loss-making share",
                config.COL_DISCOUNT_BAND: "Discount"},
        color_discrete_sequence=[COLOR_LOSS],
    )
    fig.update_layout(height=CHART_HEIGHT, yaxis_tickformat=".0%")
    right.plotly_chart(fig, width="stretch")

    scatter = an.discount_vs_margin_scatter(df)
    fig = px.scatter(
        scatter, x="avg_discount", y="profit_margin", size="revenue",
        color="profit_margin", color_continuous_scale=PROFIT_SCALE,
        color_continuous_midpoint=0, text=config.COL_SUB_CATEGORY,
        size_max=45, title="Discount vs margin by sub-category (size = revenue)",
        labels={"avg_discount": "Average discount", "profit_margin": "Profit margin"},
    )
    fig.update_traces(textposition="top center", textfont_size=9)
    fig.add_hline(y=0, line_width=1, line_color="black")
    fig.update_layout(height=460, xaxis_tickformat=".0%", yaxis_tickformat=".0%",
                      coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch")

    st.subheader("Loss-making products")
    st.caption(
        f"Products losing money across at least "
        f"{config.MIN_ORDERS_FOR_RANKING} orders — systematic pricing "
        f"failures rather than one-off bad deals."
    )
    worst = an.over_discounted_groups(df, by=config.COL_PRODUCT_NAME, top_n=15)
    if worst.empty:
        st.info("No product meets the loss-making threshold for this selection.")
    else:
        worst = to_percentage_points(worst, ["profit_margin", "avg_discount"])
        st.dataframe(
            worst[[config.COL_PRODUCT_NAME, "revenue", "profit",
                   "profit_margin", "avg_discount", "orders"]],
            hide_index=True,
            width="stretch",
            column_config={
                config.COL_PRODUCT_NAME: "Product",
                "revenue": st.column_config.NumberColumn("Revenue", format="$%.0f"),
                "profit": st.column_config.NumberColumn("Profit", format="$%.0f"),
                "profit_margin": st.column_config.NumberColumn("Margin", format="%.1f%%"),
                "avg_discount": st.column_config.NumberColumn("Avg discount", format="%.1f%%"),
                "orders": st.column_config.NumberColumn("Orders"),
            },
        )


def render_trends_tab(df: pd.DataFrame) -> None:
    """Time series, year-on-year growth and seasonality."""
    monthly = an.monthly_trend(df)
    fig = px.line(
        monthly, x=config.COL_YEAR_MONTH, y=["revenue", "profit"],
        title="Monthly revenue and profit",
        color_discrete_sequence=[COLOR_REVENUE, COLOR_PROFIT],
        labels={"value": "USD", "variable": "", config.COL_YEAR_MONTH: ""},
    )
    fig.update_layout(height=CHART_HEIGHT)
    st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)

    seasonal = an.seasonality_by_month(df)
    fig = px.bar(
        seasonal, x=config.COL_MONTH_NAME, y="avg_revenue",
        title="Average revenue by calendar month",
        color_discrete_sequence=[COLOR_REVENUE],
        labels={"avg_revenue": "Average revenue", config.COL_MONTH_NAME: ""},
    )
    fig.add_hline(
        y=seasonal["avg_revenue"].mean(), line_dash="dash", line_color=COLOR_LOSS,
    )
    fig.update_layout(height=CHART_HEIGHT)
    left.plotly_chart(fig, width="stretch")

    quarterly = an.quarterly_summary(df)
    heat = quarterly.pivot(
        index=config.COL_YEAR, columns=config.COL_QUARTER, values="revenue"
    )
    fig = px.imshow(
        heat, text_auto=",.0f", aspect="auto", color_continuous_scale="Blues",
        title="Revenue by quarter and year",
        labels={"x": "Quarter", "y": "Year", "color": "Revenue"},
    )
    fig.update_layout(height=CHART_HEIGHT)
    right.plotly_chart(fig, width="stretch")

    yearly = to_percentage_points(
        an.yearly_trend(df), ["profit_margin", "revenue_growth"]
    )
    st.dataframe(
        yearly[[config.COL_YEAR, "revenue", "profit", "profit_margin",
                "orders", "revenue_growth"]],
        hide_index=True,
        width="stretch",
        column_config={
            config.COL_YEAR: st.column_config.NumberColumn("Year", format="%d"),
            "revenue": st.column_config.NumberColumn("Revenue", format="$%.0f"),
            "profit": st.column_config.NumberColumn("Profit", format="$%.0f"),
            "profit_margin": st.column_config.NumberColumn("Margin", format="%.1f%%"),
            "orders": st.column_config.NumberColumn("Orders"),
            "revenue_growth": st.column_config.NumberColumn("YoY growth", format="%.1f%%"),
        },
    )


# --- Entry point -----------------------------------------------------------


def main() -> None:
    """Compose the dashboard."""
    df = get_data()
    filtered = render_sidebar(df)

    st.title("📊 Superstore Sales Analytics")
    st.caption(
        "Regional performance, discount efficiency and seasonality across "
        "51 290 global order lines, 2011–2014."
    )

    if filtered.empty:
        st.warning("No orders match the current filters. Widen the selection.")
        return

    render_kpis(filtered)
    st.divider()

    performance, discounts, trends = st.tabs(
        ["Performance", "Discount efficiency", "Trends & seasonality"]
    )
    with performance:
        render_performance_tab(filtered)
    with discounts:
        render_discount_tab(filtered)
    with trends:
        render_trends_tab(filtered)


if __name__ == "__main__":
    main()

