"""Central configuration: paths, column names and analysis constants.

Keeping these in one place means the notebook, the modules and the Streamlit
app all refer to the same literals instead of scattering magic strings.
"""

from pathlib import Path

# --- Paths -----------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_FILE = DATA_DIR / "SuperStore_Orders.csv"

# The Kaggle export is Latin-1 encoded; reading it as UTF-8 raises a
# UnicodeDecodeError on accented customer and product names.
RAW_ENCODING = "latin-1"

# Dates are day-first (e.g. "06-01-2011" is 6 January). Parsing without an
# explicit format silently swaps day and month for the first 12 days of a month.
RAW_DATE_FORMAT = "%d-%m-%Y"

# --- Raw column names ------------------------------------------------------

COL_ORDER_ID = "order_id"
COL_ORDER_DATE = "order_date"
COL_SHIP_DATE = "ship_date"
COL_SHIP_MODE = "ship_mode"
COL_CUSTOMER = "customer_name"
COL_SEGMENT = "segment"
COL_STATE = "state"
COL_COUNTRY = "country"
COL_MARKET = "market"
COL_REGION = "region"
COL_PRODUCT_ID = "product_id"
COL_CATEGORY = "category"
COL_SUB_CATEGORY = "sub_category"
COL_PRODUCT_NAME = "product_name"
COL_SALES = "sales"
COL_QUANTITY = "quantity"
COL_DISCOUNT = "discount"
COL_PROFIT = "profit"
COL_SHIPPING_COST = "shipping_cost"
COL_ORDER_PRIORITY = "order_priority"

# Columns stored as text in the raw file but semantically numeric.
# `sales` uses thousands separators ("1,275"), `shipping_cost` is padded
# with spaces (" 35.46 ").
TEXT_NUMERIC_COLUMNS = [COL_SALES, COL_SHIPPING_COST]

DATE_COLUMNS = [COL_ORDER_DATE, COL_SHIP_DATE]

# A row is uniquely identified by the product line within an order.
ORDER_LINE_KEY = [COL_ORDER_ID, COL_PRODUCT_ID]

# --- Derived column names --------------------------------------------------

COL_YEAR = "year"
COL_QUARTER = "quarter"
COL_MONTH = "month"
COL_MONTH_NAME = "month_name"
COL_YEAR_MONTH = "year_month"
COL_PROFIT_MARGIN = "profit_margin"
COL_IS_LOSS = "is_loss"
COL_SHIPPING_DAYS = "shipping_days"
COL_DISCOUNT_BAND = "discount_band"

# `region` values are only unique *within* a market: "Central", "North" and
# "South" each occur under EU, LATAM and US. Grouping on `region` alone
# silently merges three different territories, so we build a qualified key.
COL_MARKET_REGION = "market_region"
MARKET_REGION_SEPARATOR = " - "

# --- Analysis constants ----------------------------------------------------

# Discount buckets used for the discount-vs-profit analysis. Upper edges are
# inclusive; 0 is kept as its own bucket because undiscounted orders behave
# very differently from lightly discounted ones.
DISCOUNT_BAND_EDGES = [-0.001, 0.0, 0.10, 0.20, 0.30, 0.50, 1.0]
DISCOUNT_BAND_LABELS = ["0%", "1-10%", "11-20%", "21-30%", "31-50%", ">50%"]

MONTH_ORDER = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

# Minimum rows a group needs before its margin is treated as meaningful.
MIN_ORDERS_FOR_RANKING = 30

DATASET_URL = "https://www.kaggle.com/datasets/aditisaxena20/superstore-sales-dataset"
