"""Load and prepare daily email volume data for Prophet forecasting.

This module provides functions to extract daily email data from the SQLite
database and transform it into Prophet-compatible DataFrames with optional
holiday and day-of-week regressors.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import pandas as pd

logger = logging.getLogger(__name__)


def load_daily_data(
    db_path: Path | str,
    start_date: str | None = None,
    end_date: str | None = None,
    target_column: str = "total_emails",
) -> pd.DataFrame:
    """Load daily email data from SQLite database.

    Args:
        db_path: Path to the SQLite database file
        start_date: Optional start date filter (YYYY-MM-DD format)
        end_date: Optional end date filter (YYYY-MM-DD format)
        target_column: Column name to use as forecast target (default: total_emails)

    Returns:
        DataFrame with columns: date, target, has_email_data, has_sla_data

    Raises:
        ValueError: If target_column doesn't exist in the days table
    """
    logger.info("Loading daily data from %s", db_path)

    with sqlite3.connect(db_path) as conn:
        # Build query with optional date filters
        query = f"""
            SELECT
                date,
                {target_column} as target,
                has_email_data,
                has_sla_data
            FROM days
            WHERE has_email_data = 1
        """

        params: list[str] = []
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date"

        df = pd.read_sql_query(query, conn, params=params)

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"])

    logger.info(
        "Loaded %d days from %s to %s (raw)",
        len(df),
        df["date"].min().strftime("%Y-%m-%d"),
        df["date"].max().strftime("%Y-%m-%d"),
    )

    # Check for nulls in target and filter them out
    null_count = df["target"].isna().sum()
    if null_count > 0:
        logger.warning(
            "Found %d null values in target column %s, filtering them out",
            null_count,
            target_column,
        )
        df = df[df["target"].notna()].copy()

    logger.info(
        "After null filtering: %d days from %s to %s",
        len(df),
        df["date"].min().strftime("%Y-%m-%d"),
        df["date"].max().strftime("%Y-%m-%d"),
    )

    return df


def _generate_holiday_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add holiday-related features to the DataFrame.

    For now, this uses a simple heuristic: weekends are holidays.
    In production, this should be replaced with actual holiday calendar.

    Args:
        df: DataFrame with a 'date' column

    Returns:
        DataFrame with added columns: is_holiday, pre_holiday, post_holiday
    """
    df = df.copy()

    # Simple heuristic: weekend = holiday (Saturday=5, Sunday=6)
    df["day_of_week"] = df["date"].dt.dayofweek
    df["is_holiday"] = (df["day_of_week"] >= 5).astype(int)

    # Pre-holiday: day before a holiday
    df["pre_holiday"] = df["is_holiday"].shift(-1, fill_value=0).astype(int)

    # Post-holiday: day after a holiday
    df["post_holiday"] = df["is_holiday"].shift(1, fill_value=0).astype(int)

    # Clean up temporary column
    df = df.drop(columns=["day_of_week"])

    logger.debug("Added holiday features: %d holidays detected", df["is_holiday"].sum())

    return df


def prepare_prophet_frame(
    df: pd.DataFrame,
    include_regressors: bool = True,
    regressor_type: Literal["holiday", "dow", "both"] = "holiday",
) -> pd.DataFrame:
    """Transform daily data into Prophet-compatible format.

    Prophet requires a DataFrame with columns:
    - ds: datetime column
    - y: target variable
    - [optional regressors]: additional features

    Args:
        df: DataFrame from load_daily_data
        include_regressors: Whether to add regressor features
        regressor_type: Type of regressors to include:
            - "holiday": is_holiday, pre_holiday, post_holiday
            - "dow": day-of-week one-hot encoding (dow_0 to dow_5)
            - "both": all regressors

    Returns:
        Prophet-ready DataFrame with ds, y, and optional regressors
    """
    prophet_df = pd.DataFrame()
    prophet_df["ds"] = df["date"]
    prophet_df["y"] = df["target"]

    if include_regressors:
        if regressor_type in ("holiday", "both"):
            # Add holiday features
            temp_df = _generate_holiday_features(df[["date"]].copy())
            prophet_df["is_holiday"] = temp_df["is_holiday"]
            prophet_df["pre_holiday"] = temp_df["pre_holiday"]
            prophet_df["post_holiday"] = temp_df["post_holiday"]

        if regressor_type in ("dow", "both"):
            # Add day-of-week one-hot encoding (Monday=0, ..., Saturday=5)
            dow = pd.get_dummies(df["date"].dt.dayofweek, prefix="dow", drop_first=False)

            # Drop Sunday (dow_6) to avoid collinearity with intercept
            if "dow_6" in dow.columns:
                dow = dow.drop(columns=["dow_6"])

            # Ensure deterministic column ordering (dow_0 ... dow_5)
            dow = dow.reindex(sorted(dow.columns), axis=1)
            prophet_df = pd.concat([prophet_df, dow], axis=1)

    logger.info("Prepared Prophet frame: shape=%s, columns=%s", prophet_df.shape, list(prophet_df.columns))

    return prophet_df


def split_train_test(
    df: pd.DataFrame,
    test_days: int = 14,
    split_method: Literal["last_n", "date"] = "last_n",
    split_date: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split data into train and test sets.

    Args:
        df: Prophet-ready DataFrame
        test_days: Number of days to reserve for testing
        split_method: How to split:
            - "last_n": Use last N days as test set
            - "date": Split at a specific date
        split_date: Date to split at (YYYY-MM-DD) when split_method="date"

    Returns:
        Tuple of (train_df, test_df)

    Raises:
        ValueError: If split_method="date" but split_date not provided
    """
    df = df.sort_values("ds").reset_index(drop=True)

    if split_method == "last_n":
        train_df = df.iloc[:-test_days].copy()
        test_df = df.iloc[-test_days:].copy()

        logger.info(
            "Split using last %d days: train=%d rows, test=%d rows",
            test_days,
            len(train_df),
            len(test_df),
        )

    elif split_method == "date":
        if split_date is None:
            raise ValueError("split_date must be provided when split_method='date'")

        split_dt = pd.to_datetime(split_date)
        train_df = df[df["ds"] < split_dt].copy()
        test_df = df[df["ds"] >= split_dt].copy()

        logger.info(
            "Split at date %s: train=%d rows, test=%d rows",
            split_date,
            len(train_df),
            len(test_df),
        )
    else:
        raise ValueError(f"Unknown split_method: {split_method}")

    return train_df, test_df
