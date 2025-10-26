"""Evaluation metrics and utilities for forecast quality assessment."""

from .metrics import calculate_metrics, calculate_baseline_metrics, compare_to_baselines
from .plots import (
    plot_forecast_vs_actual,
    plot_residuals,
    plot_components,
    plot_dow_performance,
)
from .cross_validation import (
    generate_expanding_window_splits,
    grid_search_prophet,
    aggregate_fold_metrics,
)
from .calibration import (
    CalibrationParameters,
    calibrate_forecasts,
    apply_calibration,
)

__all__ = [
    "calculate_metrics",
    "calculate_baseline_metrics",
    "compare_to_baselines",
    "plot_forecast_vs_actual",
    "plot_residuals",
    "plot_components",
    "plot_dow_performance",
    "generate_expanding_window_splits",
    "grid_search_prophet",
    "aggregate_fold_metrics",
    "CalibrationParameters",
    "calibrate_forecasts",
    "apply_calibration",
]
