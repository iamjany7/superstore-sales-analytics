"""Loading the raw Superstore export and exposing an analysis-ready frame."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config
from .data_cleaning import clean_orders


def load_raw_data(path: str | Path | None = None) -> pd.DataFrame:
    """Read the raw Superstore CSV exactly as shipped, with no type coercion.

    Args:
        path: Location of the CSV. Defaults to ``config.RAW_DATA_FILE``.

    Returns:
        The raw frame, all columns as written in the file.

    Raises:
        FileNotFoundError: If the CSV is not present.
    """
    csv_path = Path(path) if path is not None else config.RAW_DATA_FILE
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {csv_path}. Download it from "
            f"{config.DATASET_URL} and place it in the data/ folder."
        )
    return pd.read_csv(csv_path, encoding=config.RAW_ENCODING)


def load_clean_data(path: str | Path | None = None) -> pd.DataFrame:
    """Load the raw CSV and return the cleaned, enriched analysis frame.

    This is the single entry point shared by the notebook and the Streamlit
    app so that both always see identical data.
    """
    return clean_orders(load_raw_data(path))


def describe_raw_data(df: pd.DataFrame) -> pd.DataFrame:
    """Summarise each column's dtype, missing values and cardinality.

    Used in the exploration notebook to document the state of the raw file.
    """
    return pd.DataFrame(
        {
            "dtype": df.dtypes.astype(str),
            "missing": df.isna().sum(),
            "missing_pct": (df.isna().mean() * 100).round(2),
            "unique": df.nunique(),
            "example": df.iloc[0],
        }
    )
