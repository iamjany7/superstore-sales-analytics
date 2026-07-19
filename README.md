# 📊 Superstore Sales Analytics

An end-to-end retail sales analysis of **51,290 global order lines (2011–2014)**, covering regional
performance, discount efficiency and seasonality — delivered as a reproducible Jupyter case study and
an interactive Streamlit dashboard.


[Dashboard preview](docs/dashboard.png)

> (https://superstore-sales-analytics-cmjkrco4r4qnklhvjjnn3e.streamlit.app/)

---

## Business questions

| # | Question | Where it's answered |
|---|----------|---------------------|
| 1 | **Regional & category performance** — which regions, categories and sub-categories drive revenue and profit? | Notebook §4 · Dashboard *Performance* tab |
| 2 | **Discount–profit efficiency** — how does discounting affect margin, and what is being over-discounted into a loss? | Notebook §5 · Dashboard *Discount efficiency* tab |
| 3 | **Sales trends & seasonality** — how do sales and profit trend over time, and are there seasonal patterns? | Notebook §6 · Dashboard *Trends & seasonality* tab |

## Key findings

- **Discounts above 20% destroy value.** Profit margin falls from **+25.3% on undiscounted lines to
  -5.6% in the 21–30% band**, and every single line discounted above 50% loses money — a **100% loss
  rate**. Discount rate and profit margin correlate at **-0.85**.
- **Revenue rankings point at the wrong category.** Furniture earns nearly as much revenue as
  Technology ($4.11M vs $4.74M) but **less than half the profit** ($287k vs $662k) — a **7.0% margin
  against 14.0%**.
- **Tables is the only loss-making sub-category**: **-$64k on $757k of revenue**, carrying the highest
  average discount of any sub-category at **29.1%** versus a 14.3% company average.
- **Growth is healthy and seasonal.** Revenue nearly doubled from **$2.26M (2011) to $4.30M (2014)**,
  compounding ~**25% a year at a stable 11–12% margin**. **Q4 peaks ~50% above average** (Nov–Dec),
  while **February is the annual trough** at roughly a third of December.

> ⚠️ **A caveat worth knowing:** the worst loss-making *individual products* average only **12–24%
> discounts** — at or below the break-even line. Those are cost/list-price problems, not discounting
> problems, and a discount ceiling alone would not fix them. See notebook §5.

## Dataset

[Superstore Sales Dataset](https://www.kaggle.com/datasets/aditisaxena20/superstore-sales-dataset) —
Kaggle, published by *aditisaxena20*. 51,290 rows × 21 columns spanning 147 countries, 7 markets and
3 product categories.

Three quirks in the raw file that the cleaning layer handles explicitly:

1. The CSV is **Latin-1 encoded** — a plain UTF-8 read raises `UnicodeDecodeError`.
2. `sales` and `shipping_cost` load as **text** (thousands separators, whitespace padding).
3. Dates are **day-first** (`06-01-2011` = 6 January), and `region` names are **only unique within a
   market** — EU, LATAM and US each have a "Central", so grouping on `region` alone silently merges
   three different territories.

## Tech stack

| Purpose | Tools |
|---------|-------|
| Analysis | Python 3.13, pandas |
| Static charts (notebook) | matplotlib, seaborn |
| Interactive charts (dashboard) | Plotly Express |
| Dashboard | Streamlit |
| Environment | venv, pinned `requirements.txt` |

## Project structure

```
.
├── app/
│   └── app.py                    # Streamlit dashboard
├── data/
│   └── SuperStore_Orders.csv     # Raw dataset
├── notebooks/
│   └── data_exploration.ipynb    # Case-study notebook (cleaning + EDA + insights)
├── src/
│   ├── config.py                 # Paths, column names, analysis constants
│   ├── data_loader.py            # Reading the raw CSV
│   ├── data_cleaning.py          # Type fixes, dedup, derived columns
│   └── analysis.py               # Reusable aggregations
├── requirements.txt              # Runtime dependencies
├── requirements-dev.txt          # + notebook tooling
└── README.md
```

**The notebook and the dashboard import the same functions from `/src`** — no analysis logic is
duplicated between them, so both are guaranteed to report identical figures.


## Dashboard features

- **Sidebar filters** — order date range, market, region, category and customer segment. The region
  list narrows to the markets you select.
- **KPI cards** — total revenue, total profit (with margin), orders, average discount and the share of
  loss-making order lines.
- **Performance tab** — revenue vs profit by category, top regions shaded by margin, sub-category
  profit ranking, and a world choropleth of profit by country.
- **Discount efficiency tab** — margin and loss rate by discount band, a discount-vs-margin bubble
  chart, and a table of systematically loss-making products.
- **Trends & seasonality tab** — monthly revenue/profit lines, average revenue by calendar month, a
  quarter-by-year heatmap, and a year-on-year growth table.

---

*Built as a portfolio project demonstrating data cleaning, exploratory analysis, modular Python and
dashboard development.*
