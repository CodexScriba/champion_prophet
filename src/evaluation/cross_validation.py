"""Cross-validation utilities for Prophet models."""

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import pandas as pd

from .metrics import calculate_metrics
from models.prophet_daily import ProphetDailyModel

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FoldSplit:
    """Represents a single expanding-window fold."""

    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    train_indices: range
    test_indices: range


@dataclass(slots=True)
class FoldResult:
    """Holds per-fold metrics and predictions."""

    fold_id: int
    split: FoldSplit
    metrics: dict[str, Any]
    forecast: pd.DataFrame


def generate_expanding_window_splits(
    df: pd.DataFrame,
    horizon: int,
    initial_train_size: int,
    max_folds: int | None = None,
) -> list[FoldSplit]:
    """Generate expanding-window splits for time series CV."""

    n_obs = len(df)
    if initial_train_size >= n_obs:
        raise ValueError("initial_train_size must be smaller than dataset length")
    if horizon <= 0:
        raise ValueError("horizon must be positive")

    splits: list[FoldSplit] = []
    train_end_idx = initial_train_size
    fold_id = 0

    while train_end_idx + horizon <= n_obs:
        test_end_idx = train_end_idx + horizon
        train_range = range(0, train_end_idx)
        test_range = range(train_end_idx, test_end_idx)

        split = FoldSplit(
            train_start=df.iloc[train_range.start]["ds"],
            train_end=df.iloc[train_range.stop - 1]["ds"],
            test_start=df.iloc[test_range.start]["ds"],
            test_end=df.iloc[test_range.stop - 1]["ds"],
            train_indices=train_range,
            test_indices=test_range,
        )
        splits.append(split)
        logger.debug(
            "Generated fold %d: train(%s→%s) test(%s→%s)",
            fold_id,
            split.train_start,
            split.train_end,
            split.test_start,
            split.test_end,
        )

        fold_id += 1
        if max_folds and fold_id >= max_folds:
            break

        train_end_idx = test_end_idx

    if not splits:
        raise ValueError("Unable to create any folds with provided configuration")

    logger.info("Generated %d expanding-window folds", len(splits))
    return splits


def run_prophet_fold(
    df: pd.DataFrame,
    split: FoldSplit,
    model_config: dict[str, Any],
    regressor_columns: Sequence[str],
) -> FoldResult:
    """Run a single Prophet fold and collect metrics."""

    train_df = df.iloc[split.train_indices].copy()
    test_df = df.iloc[split.test_indices].copy()

    model = ProphetDailyModel(**model_config)
    if regressor_columns:
        model.add_regressors(list(regressor_columns))

    model.fit(train_df)
    forecast = model.forecast_holdout(test_df)

    forecast_df = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].merge(
        test_df[["ds", "y"]], on="ds", how="left"
    )

    metrics = calculate_metrics(
        y_true=forecast_df["y"],
        y_pred=forecast_df["yhat"],
        y_lower=forecast_df["yhat_lower"],
        y_upper=forecast_df["yhat_upper"],
        dates=forecast_df["ds"],
    )

    return FoldResult(
        fold_id=len(forecast_df),  # placeholder, caller can override
        split=split,
        metrics=metrics,
        forecast=forecast_df,
    )


def aggregate_fold_metrics(fold_results: Iterable[FoldResult]) -> dict[str, Any]:
    """Aggregate metrics across folds (simple average)."""

    metrics_list = [fold.metrics for fold in fold_results]
    if not metrics_list:
        raise ValueError("No fold metrics to aggregate")

    aggregated: dict[str, Any] = {}
    keys = metrics_list[0].keys()
    for key in keys:
        values = [metrics[key] for metrics in metrics_list if key in metrics]
        if values and isinstance(values[0], (int, float)):
            aggregated[key] = sum(values) / len(values)

    aggregated["n_folds"] = len(metrics_list)
    return aggregated


def grid_search_prophet(
    df: pd.DataFrame,
    splits: list[FoldSplit],
    param_grid: dict[str, Sequence[Any]],
    regressor_columns: Sequence[str],
) -> tuple[dict[str, Any], list[FoldResult], list[dict[str, Any]]]:
    """Run grid search over Prophet hyperparameters."""

    grid_keys = list(param_grid.keys())
    all_combinations = list(itertools.product(*(param_grid[key] for key in grid_keys)))
    logger.info("Evaluating %d hyperparameter combinations", len(all_combinations))

    best_config: dict[str, Any] | None = None
    best_score: float | None = None
    best_fold_results: list[FoldResult] = []
    history: list[dict[str, Any]] = []

    for combo in all_combinations:
        config = dict(zip(grid_keys, combo))
        # Add defaults for any unspecified params
        config.setdefault("interval_width", 0.80)
        config.setdefault("weekly_seasonality", True)
        config.setdefault("yearly_seasonality", False)
        config.setdefault("daily_seasonality", False)
        config.setdefault("growth", "linear")

        fold_results: list[FoldResult] = []
        for fold_idx, split in enumerate(splits):
            result = run_prophet_fold(df, split, config, regressor_columns)
            result.fold_id = fold_idx
            fold_results.append(result)

        aggregated = aggregate_fold_metrics(fold_results)
        score = aggregated["mae"]
        history.append({"config": config, "metrics": aggregated})

        logger.info(
            "Grid combo %s → MAE %.3f, Bias %.3f, Coverage %.1f%%",
            config,
            aggregated["mae"],
            aggregated.get("bias"),
            aggregated.get("coverage_percent"),
        )

        if best_score is None or score < best_score:
            best_score = score
            best_config = config
            best_fold_results = fold_results

    if best_config is None:
        raise RuntimeError("Grid search failed to evaluate any configuration")

    logger.info("Best config: %s (MAE %.3f)", best_config, best_score)
    return best_config, best_fold_results, history
