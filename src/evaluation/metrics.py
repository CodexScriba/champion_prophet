"""Forecast evaluation metrics for Prophet models.

This module provides functions to calculate standard forecasting metrics
including MAE, RMSE, sMAPE, bias, coverage, and R², plus comparison
against naive baselines.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logger = logging.getLogger(__name__)


def calculate_mae(y_true: pd.Series | np.ndarray, y_pred: pd.Series | np.ndarray) -> float:
    """Calculate Mean Absolute Error."""
    return float(mean_absolute_error(y_true, y_pred))


def calculate_rmse(y_true: pd.Series | np.ndarray, y_pred: pd.Series | np.ndarray) -> float:
    """Calculate Root Mean Squared Error."""
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def calculate_smape(y_true: pd.Series | np.ndarray, y_pred: pd.Series | np.ndarray) -> float:
    """Calculate Symmetric Mean Absolute Percentage Error.

    sMAPE = 100 * mean(2 * |y_true - y_pred| / (|y_true| + |y_pred|))
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    numerator = np.abs(y_true - y_pred)
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0

    # Avoid division by zero
    denominator = np.where(denominator == 0, 1e-10, denominator)

    smape = 100 * np.mean(numerator / denominator)
    return float(smape)


def calculate_bias(y_true: pd.Series | np.ndarray, y_pred: pd.Series | np.ndarray) -> float:
    """Calculate forecast bias (mean error).

    Positive bias = over-forecasting
    Negative bias = under-forecasting
    """
    return float(np.mean(y_pred - y_true))


def calculate_coverage(
    y_true: pd.Series | np.ndarray,
    y_lower: pd.Series | np.ndarray,
    y_upper: pd.Series | np.ndarray,
) -> float:
    """Calculate prediction interval coverage.

    Returns the proportion of actual values that fall within the
    prediction intervals.

    Args:
        y_true: Actual values
        y_lower: Lower bound of prediction interval
        y_upper: Upper bound of prediction interval

    Returns:
        Coverage as a proportion between 0 and 1
    """
    y_true = np.asarray(y_true)
    y_lower = np.asarray(y_lower)
    y_upper = np.asarray(y_upper)

    within_interval = (y_true >= y_lower) & (y_true <= y_upper)
    coverage = np.mean(within_interval)

    return float(coverage)


def calculate_r2(y_true: pd.Series | np.ndarray, y_pred: pd.Series | np.ndarray) -> float:
    """Calculate R-squared (coefficient of determination)."""
    return float(r2_score(y_true, y_pred))


def calculate_metrics(
    y_true: pd.Series | np.ndarray,
    y_pred: pd.Series | np.ndarray,
    y_lower: pd.Series | np.ndarray | None = None,
    y_upper: pd.Series | np.ndarray | None = None,
    dates: pd.Series | None = None,
) -> dict[str, Any]:
    """Calculate all standard forecast metrics.

    Args:
        y_true: Actual values
        y_pred: Predicted values
        y_lower: Lower bound of prediction interval (optional)
        y_upper: Upper bound of prediction interval (optional)
        dates: Date column for day-of-week breakdown (optional)

    Returns:
        Dictionary containing all metrics
    """
    metrics = {
        "mae": calculate_mae(y_true, y_pred),
        "rmse": calculate_rmse(y_true, y_pred),
        "smape": calculate_smape(y_true, y_pred),
        "bias": calculate_bias(y_true, y_pred),
        "r2": calculate_r2(y_true, y_pred),
        "n_samples": len(y_true),
    }

    # Add coverage if intervals provided
    if y_lower is not None and y_upper is not None:
        metrics["coverage"] = calculate_coverage(y_true, y_lower, y_upper)
        metrics["coverage_percent"] = metrics["coverage"] * 100

    # Add day-of-week breakdown if dates provided
    if dates is not None:
        metrics["dow_breakdown"] = _calculate_dow_metrics(y_true, y_pred, dates)

    logger.info(
        "Calculated metrics: MAE=%.2f, RMSE=%.2f, sMAPE=%.2f%%, Bias=%.2f, R²=%.4f",
        metrics["mae"],
        metrics["rmse"],
        metrics["smape"],
        metrics["bias"],
        metrics["r2"],
    )

    if "coverage" in metrics:
        logger.info("Coverage: %.1f%%", metrics["coverage_percent"])

    return metrics


def _calculate_dow_metrics(
    y_true: pd.Series | np.ndarray,
    y_pred: pd.Series | np.ndarray,
    dates: pd.Series,
) -> dict[str, dict[str, float]]:
    """Calculate metrics broken down by day of week.

    Args:
        y_true: Actual values
        y_pred: Predicted values
        dates: Date column (will extract day of week)

    Returns:
        Dictionary mapping day names to metrics dict
    """
    dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    df = pd.DataFrame(
        {
            "y_true": y_true,
            "y_pred": y_pred,
            "dow": pd.to_datetime(dates).dt.dayofweek,
        }
    )

    dow_metrics = {}
    for dow in range(7):
        dow_data = df[df["dow"] == dow]
        if len(dow_data) == 0:
            continue

        dow_metrics[dow_names[dow]] = {
            "mae": calculate_mae(dow_data["y_true"], dow_data["y_pred"]),
            "bias": calculate_bias(dow_data["y_true"], dow_data["y_pred"]),
            "n_samples": len(dow_data),
        }

    return dow_metrics


def calculate_baseline_metrics(
    y_true: pd.Series | np.ndarray,
    dates: pd.Series | None,
    evaluation_start_index: int | None = None,
    seasonal_period: int = 7,
) -> dict[str, dict[str, float]]:
    """Calculate naive baseline metrics for comparison.

    Baselines:
    - Seasonal naive: Use value from 7 days ago
    - Moving average: 7-day trailing average

    Args:
        y_true: Actual values
        dates: Date column (ignored, kept for API parity)
        evaluation_start_index: Index in y_true where evaluation should begin (e.g., start of test set)
        seasonal_period: Seasonal lag to use for naive baseline (default: 7 days)

    Returns:
        Dictionary with baseline metrics
    """
    y_true = np.asarray(y_true)
    n_obs = len(y_true)

    baselines: dict[str, dict[str, float]] = {}

    if n_obs == 0:
        logger.warning("No observations provided to baseline metrics")
        return baselines

    eval_start = evaluation_start_index or 0
    if eval_start < 0:
        raise ValueError("evaluation_start_index must be non-negative")
    if eval_start >= n_obs:
        logger.warning("evaluation_start_index (%d) exceeds series length (%d)", eval_start, n_obs)
        return baselines

    eval_indices = np.arange(eval_start, n_obs, dtype=int)

    # Seasonal naive (7-day lag)
    if n_obs > seasonal_period:
        seasonal_naive_pred = np.roll(y_true, seasonal_period)

        # Only evaluate indices that have a full seasonal history
        valid_indices = np.arange(seasonal_period, n_obs, dtype=int)
        valid_eval_indices = np.intersect1d(valid_indices, eval_indices, assume_unique=True)

        if valid_eval_indices.size > 0:
            baselines["seasonal_naive"] = {
                "mae": calculate_mae(y_true[valid_eval_indices], seasonal_naive_pred[valid_eval_indices]),
                "rmse": calculate_rmse(y_true[valid_eval_indices], seasonal_naive_pred[valid_eval_indices]),
                "bias": calculate_bias(y_true[valid_eval_indices], seasonal_naive_pred[valid_eval_indices]),
            }

    # Moving average (7-day)
    if n_obs > seasonal_period:
        ma_pred = np.array(
            [
                np.mean(y_true[max(0, i - seasonal_period) : i]) if i > 0 else y_true[0]
                for i in range(n_obs)
            ]
        )

        valid_indices = np.arange(seasonal_period, n_obs, dtype=int)
        valid_eval_indices = np.intersect1d(valid_indices, eval_indices, assume_unique=True)

        if valid_eval_indices.size > 0:
            baselines["moving_average_7"] = {
                "mae": calculate_mae(y_true[valid_eval_indices], ma_pred[valid_eval_indices]),
                "rmse": calculate_rmse(y_true[valid_eval_indices], ma_pred[valid_eval_indices]),
                "bias": calculate_bias(y_true[valid_eval_indices], ma_pred[valid_eval_indices]),
            }

    logger.info("Calculated baseline metrics for %d baselines", len(baselines))

    return baselines


def compare_to_baselines(
    model_metrics: dict[str, float],
    baseline_metrics: dict[str, dict[str, float]],
    champion_mae: float = 33.66,
) -> dict[str, Any]:
    """Compare model metrics against baselines and champion.

    Args:
        model_metrics: Metrics from the Prophet model
        baseline_metrics: Metrics from naive baselines
        champion_mae: MAE from current champion (default: AutoARIMA 33.66)

    Returns:
        Dictionary with comparison results and improvement percentages
    """
    model_mae = model_metrics["mae"]

    comparison = {
        "model_mae": model_mae,
        "champion_mae": champion_mae,
        "baselines": {},
        "improvements": {},
    }

    # Compare to champion
    if champion_mae > 0:
        improvement_pct = ((champion_mae - model_mae) / champion_mae) * 100
        comparison["improvements"]["vs_champion"] = {
            "mae_diff": model_mae - champion_mae,
            "improvement_pct": improvement_pct,
            "is_better": model_mae < champion_mae,
        }

    # Compare to baselines
    for baseline_name, baseline_vals in baseline_metrics.items():
        baseline_mae = baseline_vals["mae"]
        comparison["baselines"][baseline_name] = baseline_mae

        improvement_pct = ((baseline_mae - model_mae) / baseline_mae) * 100
        comparison["improvements"][f"vs_{baseline_name}"] = {
            "mae_diff": model_mae - baseline_mae,
            "improvement_pct": improvement_pct,
            "is_better": model_mae < baseline_mae,
        }

    logger.info("Comparison summary:")
    logger.info("  Model MAE: %.2f", model_mae)
    logger.info("  Champion MAE: %.2f (%.1f%% diff)", champion_mae, comparison["improvements"]["vs_champion"]["improvement_pct"])

    for baseline_name in baseline_metrics:
        key = f"vs_{baseline_name}"
        logger.info(
            "  %s: %.1f%% improvement",
            baseline_name,
            comparison["improvements"][key]["improvement_pct"],
        )

    return comparison
