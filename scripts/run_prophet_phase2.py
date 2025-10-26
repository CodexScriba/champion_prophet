#!/usr/bin/env python3
"""Phase 2 workflow: cross-validation, hyperparameter tuning, and calibration."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    from champion_prophet.config import (
        configure_logging,
        ensure_directories,
        load_settings,
        set_global_seed,
    )
    from data.daily_loader import load_daily_data, prepare_prophet_frame, split_train_test
    from evaluation.calibration import apply_calibration, calibrate_forecasts
    from evaluation.cross_validation import (
        aggregate_fold_metrics,
        generate_expanding_window_splits,
        grid_search_prophet,
    )
    from evaluation.metrics import (
        calculate_baseline_metrics,
        calculate_metrics,
        compare_to_baselines,
    )
    from evaluation.plots import (
        plot_components,
        plot_dow_performance,
        plot_forecast_vs_actual,
        plot_residuals,
    )
    from models.prophet_daily import ProphetDailyModel
except ImportError:
    import sys

    REPO_ROOT = Path(__file__).resolve().parents[1]
    SRC_PATH = REPO_ROOT / "src"
    if str(SRC_PATH) not in sys.path:
        sys.path.insert(0, str(SRC_PATH))

    from champion_prophet.config import (
        configure_logging,
        ensure_directories,
        load_settings,
        set_global_seed,
    )
    from data.daily_loader import load_daily_data, prepare_prophet_frame, split_train_test
    from evaluation.calibration import apply_calibration, calibrate_forecasts
    from evaluation.cross_validation import (
        aggregate_fold_metrics,
        generate_expanding_window_splits,
        grid_search_prophet,
    )
    from evaluation.metrics import (
        calculate_baseline_metrics,
        calculate_metrics,
        compare_to_baselines,
    )
    from evaluation.plots import (
        plot_components,
        plot_dow_performance,
        plot_forecast_vs_actual,
        plot_residuals,
    )
    from models.prophet_daily import ProphetDailyModel

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 2 Prophet workflow: CV, tuning, calibration, hold-out evaluation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--target-column", type=str, default="total_emails")
    parser.add_argument("--test-days", type=int, default=14, help="Hold-out horizon for evaluation")
    parser.add_argument("--initial-train-size", type=int, default=56, help="Minimum train window for CV folds")
    parser.add_argument("--max-folds", type=int, default=4, help="Maximum number of CV folds to evaluate")
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional run identifier (defaults to timestamp)",
    )
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()

    settings = load_settings()
    ensure_directories(settings)
    set_global_seed(settings.random_seed)

    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info("=" * 80)
    logger.info("Prophet Phase 2 Run | run_id=%s", run_id)
    logger.info("=" * 80)

    # ------------------------------------------------------------------
    # Load & prepare data
    # ------------------------------------------------------------------
    raw_df = load_daily_data(settings.database_path, target_column=args.target_column)
    prophet_df = prepare_prophet_frame(raw_df, include_regressors=True, regressor_type="both")
    regressor_cols = [col for col in prophet_df.columns if col not in ("ds", "y")]

    logger.info("Regressor columns: %s", regressor_cols)

    test_days = args.test_days
    cv_df = prophet_df.iloc[:-test_days].copy()

    splits = generate_expanding_window_splits(
        cv_df,
        horizon=test_days,
        initial_train_size=args.initial_train_size,
        max_folds=args.max_folds,
    )

    param_grid = {
        "changepoint_prior_scale": [0.01, 0.05, 0.1],
        "seasonality_prior_scale": [5.0, 10.0, 15.0],
        "seasonality_mode": ["additive", "multiplicative"],
        "interval_width": [0.80],
    }

    best_config, best_fold_results, history = grid_search_prophet(
        cv_df,
        splits,
        param_grid,
        regressor_columns=regressor_cols,
    )

    aggregated_cv_metrics = aggregate_fold_metrics(best_fold_results)
    logger.info("Best CV metrics: %s", aggregated_cv_metrics)

    cv_predictions = pd.concat(
        [fold.forecast.assign(fold=fold.fold_id) for fold in best_fold_results],
        ignore_index=True,
    )

    calibration = calibrate_forecasts(cv_predictions, settings.coverage_target)
    logger.info(
        "Calibration: interval_scale=%.3f (observed coverage %.3f → target %.3f)",
        calibration.interval_scale,
        calibration.observed_coverage,
        calibration.target_coverage,
    )
    logger.info("Calibration DOW bias adjustments: %s", calibration.dow_bias)

    # ------------------------------------------------------------------
    # Hold-out evaluation with best config
    # ------------------------------------------------------------------
    train_df, test_df = split_train_test(prophet_df, test_days=test_days)

    final_model = ProphetDailyModel(**best_config)
    if regressor_cols:
        final_model.add_regressors(regressor_cols)
    final_model.fit(train_df)

    test_forecast = final_model.forecast_holdout(test_df)
    holdout_raw = test_forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].merge(
        test_df[["ds", "y"]], on="ds", how="left"
    )

    raw_metrics = calculate_metrics(
        y_true=holdout_raw["y"],
        y_pred=holdout_raw["yhat"],
        y_lower=holdout_raw["yhat_lower"],
        y_upper=holdout_raw["yhat_upper"],
        dates=holdout_raw["ds"],
    )

    calibrated_df = holdout_raw[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    calibrated_df = apply_calibration(calibrated_df, calibration)
    calibrated_df["y"] = holdout_raw["y"].values

    calibrated_metrics = calculate_metrics(
        y_true=calibrated_df["y"],
        y_pred=calibrated_df["yhat"],
        y_lower=calibrated_df["yhat_lower"],
        y_upper=calibrated_df["yhat_upper"],
        dates=calibrated_df["ds"],
    )

    # Baselines & champion comparison
    baseline_metrics = calculate_baseline_metrics(
        y_true=prophet_df["y"],
        dates=prophet_df["ds"],
        evaluation_start_index=len(train_df),
    )
    raw_comparison = compare_to_baselines(raw_metrics, baseline_metrics)
    calibrated_comparison = compare_to_baselines(calibrated_metrics, baseline_metrics)

    # ------------------------------------------------------------------
    # Artifact persistence
    # ------------------------------------------------------------------
    metrics_payload = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "best_config": best_config,
        "cv_metrics": aggregated_cv_metrics,
        "cv_history": history,
        "calibration": {
            "dow_bias": calibration.dow_bias,
            "interval_scale": calibration.interval_scale,
            "observed_coverage": calibration.observed_coverage,
            "target_coverage": calibration.target_coverage,
        },
        "holdout_raw": {"metrics": raw_metrics, "comparison": raw_comparison},
        "holdout_calibrated": {"metrics": calibrated_metrics, "comparison": calibrated_comparison},
    }

    metrics_path = settings.metrics_dir / f"prophet_phase2_metrics_{run_id}.json"
    with open(metrics_path, "w") as fh:
        json.dump(metrics_payload, fh, indent=2, default=str)
    logger.info("Metrics saved to %s", metrics_path)

    forecast_export = holdout_raw.copy()
    forecast_export.rename(
        columns={
            "yhat": "yhat_raw",
            "yhat_lower": "yhat_lower_raw",
            "yhat_upper": "yhat_upper_raw",
        },
        inplace=True,
    )
    forecast_export["yhat_calibrated"] = calibrated_df["yhat"]
    forecast_export["yhat_lower_calibrated"] = calibrated_df["yhat_lower"]
    forecast_export["yhat_upper_calibrated"] = calibrated_df["yhat_upper"]
    forecast_export["bias_adjustment"] = calibrated_df.get("bias_adjustment", 0.0)
    forecast_export["interval_scale"] = calibration.interval_scale

    forecast_path = settings.artifacts_dir / f"prophet_phase2_forecast_{run_id}.csv"
    forecast_export.to_csv(forecast_path, index=False)
    logger.info("Forecast export saved to %s", forecast_path)

    # CV predictions (for diagnostics)
    cv_predictions_path = settings.artifacts_dir / f"prophet_phase2_cv_predictions_{run_id}.csv"
    cv_predictions.to_csv(cv_predictions_path, index=False)
    logger.info("CV predictions saved to %s", cv_predictions_path)

    # Plot diagnostics (calibrated)
    plot_forecast_vs_actual(
        dates=calibrated_df["ds"],
        y_true=calibrated_df["y"],
        y_pred=calibrated_df["yhat"],
        y_lower=calibrated_df["yhat_lower"],
        y_upper=calibrated_df["yhat_upper"],
        train_end_date=train_df["ds"].max(),
        title=f"Prophet Forecast vs Actual (Calibrated) – {run_id}",
        save_path=settings.plots_dir / f"phase2_forecast_{run_id}.png",
    )

    plot_residuals(
        dates=calibrated_df["ds"],
        y_true=calibrated_df["y"],
        y_pred=calibrated_df["yhat"],
        title=f"Residual Diagnostics (Calibrated) – {run_id}",
        save_path=settings.plots_dir / f"phase2_residuals_{run_id}.png",
    )

    full_future = final_model.model.make_future_dataframe(periods=0)
    for col in regressor_cols:
        if col in train_df.columns:
            full_future[col] = train_df[col].values
    components = final_model.get_components(final_model.model.predict(full_future))
    plot_components(
        components_df=components,
        title=f"Prophet Components – {run_id}",
        save_path=settings.plots_dir / f"phase2_components_{run_id}.png",
    )

    if "dow_breakdown" in calibrated_metrics:
        plot_dow_performance(
            dow_metrics=calibrated_metrics["dow_breakdown"],
            title=f"Day-of-Week Performance (Calibrated) – {run_id}",
            save_path=settings.plots_dir / f"phase2_dow_{run_id}.png",
        )

    logger.info("=" * 80)
    logger.info("Hold-out raw metrics: %s", raw_metrics)
    logger.info("Hold-out calibrated metrics: %s", calibrated_metrics)
    logger.info("=" * 80)
    logger.info("Phase 2 run completed")


if __name__ == "__main__":
    main()
