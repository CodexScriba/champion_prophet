from __future__ import annotations

import pandas as pd

from data.daily_loader import prepare_prophet_frame


def test_prepare_prophet_frame_dow_regressors() -> None:
    dates = pd.date_range("2025-01-06", periods=14, freq="D")  # start on Monday
    df = pd.DataFrame({"date": dates, "target": range(len(dates))})

    result = prepare_prophet_frame(df, include_regressors=True, regressor_type="dow")

    expected_columns = {"ds", "y", "dow_0", "dow_1", "dow_2", "dow_3", "dow_4", "dow_5"}
    assert expected_columns.issubset(result.columns)
    assert "dow_6" not in result.columns
    row_sums = result[["dow_0", "dow_1", "dow_2", "dow_3", "dow_4", "dow_5"]].sum(axis=1)
    assert row_sums.isin({0, 1}).all()
    sundays = result["ds"].dt.dayofweek == 6
    assert (row_sums[sundays] == 0).all()
