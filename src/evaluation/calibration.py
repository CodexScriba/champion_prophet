"""Calibration utilities for Prophet forecasts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd

from .metrics import calculate_coverage


@dataclass(slots=True)
class CalibrationParameters:
    """Holds bias and interval adjustments."""

    dow_bias: Dict[int, float]
    interval_scale: float
    target_coverage: float
    observed_coverage: float


def compute_dow_bias(residuals: pd.Series, dates: pd.Series, shrinkage: float = 1.0) -> dict[int, float]:
    """Compute mean residual per day-of-week."""

    df = pd.DataFrame({"residual": residuals, "dow": pd.to_datetime(dates).dt.dayofweek})
    bias = df.groupby("dow")["residual"].mean().to_dict()
    return {int(k): float(v * shrinkage) for k, v in bias.items()}


def apply_dow_bias(forecast_df: pd.DataFrame, dow_bias: dict[int, float]) -> pd.DataFrame:
    """Adjust forecast by adding DOW bias to mean and bounds."""

    df = forecast_df.copy()
    dows = pd.to_datetime(df["ds"]).dt.dayofweek
    adjustments = dows.map(dow_bias).fillna(0.0)

    for col in ["yhat", "yhat_lower", "yhat_upper"]:
        df[col] = df[col] + adjustments

    df["bias_adjustment"] = adjustments
    return df


def compute_interval_scale(
    y_true: pd.Series,
    y_lower: pd.Series,
    y_upper: pd.Series,
    target_coverage: float,
    tolerance: float = 0.02,
    min_scale: float = 0.8,
    max_scale: float = 1.2,
    gain: float = 0.5,
) -> tuple[float, float]:
    """Compute scaling factor to hit desired coverage."""

    observed_coverage = calculate_coverage(y_true, y_lower, y_upper)
    if observed_coverage <= 0:
        scale = 1.0
    else:
        if abs(target_coverage - observed_coverage) <= tolerance:
            scale = 1.0
        else:
            adjustment = (target_coverage - observed_coverage) * gain
            scale = float(np.clip(1.0 + adjustment, min_scale, max_scale))

    return float(scale), float(observed_coverage)


def apply_interval_scaling(
    forecast_df: pd.DataFrame,
    interval_scale: float,
) -> pd.DataFrame:
    """Scale prediction intervals around the adjusted mean."""

    df = forecast_df.copy()
    center = df["yhat"]
    half_width = (df["yhat_upper"] - df["yhat_lower"]) / 2.0
    half_width = half_width * interval_scale

    df["yhat_lower"] = center - half_width
    df["yhat_upper"] = center + half_width
    df["interval_scale"] = interval_scale
    return df


def calibrate_forecasts(
    cv_predictions: pd.DataFrame,
    target_coverage: float,
    bias_shrinkage: float = 0.5,
) -> CalibrationParameters:
    """Derive calibration parameters from cross-validation predictions."""

    residuals = cv_predictions["y"] - cv_predictions["yhat"]
    dow_bias = compute_dow_bias(residuals, cv_predictions["ds"], shrinkage=bias_shrinkage)

    interval_scale, observed = compute_interval_scale(
        y_true=cv_predictions["y"],
        y_lower=cv_predictions["yhat_lower"],
        y_upper=cv_predictions["yhat_upper"],
        target_coverage=target_coverage,
    )

    return CalibrationParameters(
        dow_bias=dow_bias,
        interval_scale=interval_scale,
        target_coverage=target_coverage,
        observed_coverage=observed,
    )


def apply_calibration(
    forecast_df: pd.DataFrame,
    calibration: CalibrationParameters,
) -> pd.DataFrame:
    """Apply bias and interval calibration to forecasts."""

    df = apply_dow_bias(forecast_df, calibration.dow_bias)
    df = apply_interval_scaling(df, calibration.interval_scale)
    return df
