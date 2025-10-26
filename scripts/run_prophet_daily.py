#!/usr/bin/env python3
"""Run baseline Prophet daily forecasting model.

This script implements Phase 1 of the Prophet challenger development:
- Load daily email volume data
- Split into train/test (last 14 days for test)
- Fit baseline Prophet model with holiday regressors
- Generate forecasts and compute metrics
- Create diagnostic plots
- Save all artifacts with timestamps
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Handle imports for both installed and development environments
try:
    from champion_prophet.config import (
        Settings,
        configure_logging,
        ensure_directories,
        load_settings,
        set_global_seed,
    )
    from data.daily_loader import load_daily_data, prepare_prophet_frame, split_train_test
    from evaluation.metrics import calculate_baseline_metrics, calculate_metrics, compare_to_baselines
    from evaluation.plots import (
        plot_components,
        plot_dow_performance,
        plot_forecast_vs_actual,
        plot_residuals,
    )
    from models.prophet_daily import ProphetDailyModel
except ImportError:
    REPO_ROOT = Path(__file__).resolve().parents[1]
    SRC_PATH = REPO_ROOT / "src"
    if str(SRC_PATH) not in sys.path:
        sys.path.insert(0, str(SRC_PATH))

    from champion_prophet.config import (
        Settings,
        configure_logging,
        ensure_directories,
        load_settings,
        set_global_seed,
    )
    from data.daily_loader import load_daily_data, prepare_prophet_frame, split_train_test
    from evaluation.metrics import calculate_baseline_metrics, calculate_metrics, compare_to_baselines
    from evaluation.plots import (
        plot_components,
        plot_dow_performance,
        plot_forecast_vs_actual,
        plot_residuals,
    )
    from models.prophet_daily import ProphetDailyModel


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run baseline Prophet daily forecasting model",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--target-column",
        type=str,
        default="total_emails",
        help="Column name to use as forecast target (default: total_emails)",
    )

    parser.add_argument(
        "--test-days",
        type=int,
        default=14,
        help="Number of days to reserve for testing",
    )

    parser.add_argument(
        "--interval-width",
        type=float,
        default=0.80,
        help="Width of prediction intervals (0.80 = 80%%)",
    )

    parser.add_argument(
        "--include-regressors",
        action="store_true",
        default=True,
        help="Include holiday regressors in the model",
    )

    parser.add_argument(
        "--regressor-type",
        type=str,
        choices=["holiday", "dow", "both"],
        default="both",
        help="Type of regressors to include",
    )

    parser.add_argument(
        "--weekly-seasonality",
        action="store_true",
        default=True,
        help="Enable Prophet weekly seasonality",
    )

    parser.add_argument(
        "--yearly-seasonality",
        action="store_true",
        default=False,
        help="Enable Prophet yearly seasonality",
    )

    parser.add_argument(
        "--changepoint-prior-scale",
        type=float,
        default=0.05,
        help="Prophet changepoint prior scale (flexibility of trend)",
    )

    parser.add_argument(
        "--seasonality-prior-scale",
        type=float,
        default=10.0,
        help="Prophet seasonality prior scale (strength of seasonality)",
    )

    parser.add_argument(
        "--seasonality-mode",
        type=str,
        choices=["additive", "multiplicative"],
        default="additive",
        help="Prophet seasonality mode",
    )

    parser.add_argument(
        "--save-plots",
        action="store_true",
        default=True,
        help="Save diagnostic plots to artifacts",
    )

    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Custom run ID (default: timestamp)",
    )

    return parser.parse_args()


def main() -> None:
    """Main execution function."""
    configure_logging()
    logger.info("=" * 80)
    logger.info("Prophet Daily Baseline - Phase 1")
    logger.info("=" * 80)

    # Parse arguments
    args = parse_args()

    # Load settings
    settings = load_settings()
    ensure_directories(settings)
    set_global_seed(settings.random_seed)

    # Generate run ID
    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info("Run ID: %s", run_id)

    # --- Step 1: Load Data ---
    logger.info("\n[Step 1] Loading daily data...")
    daily_df = load_daily_data(settings.database_path, target_column=args.target_column)

    logger.info("Data shape: %s", daily_df.shape)
    logger.info("Date range: %s to %s", daily_df["date"].min(), daily_df["date"].max())

    # --- Step 2: Prepare Prophet Frame ---
    logger.info("\n[Step 2] Preparing Prophet-ready dataframe...")
    prophet_df = prepare_prophet_frame(
        daily_df,
        include_regressors=args.include_regressors,
        regressor_type=args.regressor_type,
    )

    logger.info("Prophet frame shape: %s", prophet_df.shape)
    logger.info("Columns: %s", list(prophet_df.columns))

    # --- Step 3: Split Train/Test ---
    logger.info("\n[Step 3] Splitting into train/test sets...")
    train_df, test_df = split_train_test(prophet_df, test_days=args.test_days)

    logger.info("Train set: %d days (%s to %s)", len(train_df), train_df["ds"].min(), train_df["ds"].max())
    logger.info("Test set: %d days (%s to %s)", len(test_df), test_df["ds"].min(), test_df["ds"].max())

    train_end_date = train_df["ds"].max()
    test_start_idx = len(train_df)

    # --- Step 4: Initialize and Train Prophet Model ---
    logger.info("\n[Step 4] Initializing Prophet model...")
    model = ProphetDailyModel(
        interval_width=args.interval_width,
        weekly_seasonality=args.weekly_seasonality,
        yearly_seasonality=args.yearly_seasonality,
        changepoint_prior_scale=args.changepoint_prior_scale,
        seasonality_prior_scale=args.seasonality_prior_scale,
        seasonality_mode=args.seasonality_mode,
    )

    # Add regressors if included
    if args.include_regressors:
        regressor_cols = [col for col in train_df.columns if col not in ["ds", "y"]]
        if regressor_cols:
            model.add_regressors(regressor_cols)
            logger.info("Added %d regressors: %s", len(regressor_cols), regressor_cols)

    # Fit model
    logger.info("Fitting Prophet model...")
    model.fit(train_df)
    logger.info("Model training complete!")

    # --- Step 5: Generate Forecasts ---
    logger.info("\n[Step 5] Generating forecasts for test period...")

    # Forecast on test set
    test_forecast = model.forecast_holdout(test_df)

    # Extract predictions and intervals
    test_pred = test_forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]
    test_pred = test_pred.merge(test_df[["ds", "y"]], on="ds", how="left")

    logger.info("Generated %d test forecasts", len(test_pred))

    # --- Step 6: Calculate Metrics ---
    logger.info("\n[Step 6] Calculating evaluation metrics...")

    # Model metrics
    metrics = calculate_metrics(
        y_true=test_pred["y"],
        y_pred=test_pred["yhat"],
        y_lower=test_pred["yhat_lower"],
        y_upper=test_pred["yhat_upper"],
        dates=test_pred["ds"],
    )

    # Baseline metrics (use full dataset for baselines)
    baseline_metrics = calculate_baseline_metrics(
        y_true=prophet_df["y"],
        dates=prophet_df["ds"],
        evaluation_start_index=test_start_idx,
    )

    # Comparison
    comparison = compare_to_baselines(metrics, baseline_metrics)

    # --- Step 7: Generate Plots ---
    if args.save_plots:
        logger.info("\n[Step 7] Generating diagnostic plots...")

        # Forecast vs actual
        plot_forecast_vs_actual(
            dates=test_pred["ds"],
            y_true=test_pred["y"],
            y_pred=test_pred["yhat"],
            y_lower=test_pred["yhat_lower"],
            y_upper=test_pred["yhat_upper"],
            train_end_date=train_end_date,
            title=f"Prophet Baseline Forecast vs Actual (Run: {run_id})",
            save_path=settings.plots_dir / f"forecast_vs_actual_{run_id}.png",
        )

        # Residuals
        plot_residuals(
            dates=test_pred["ds"],
            y_true=test_pred["y"],
            y_pred=test_pred["yhat"],
            title=f"Forecast Residuals (Run: {run_id})",
            save_path=settings.plots_dir / f"residuals_{run_id}.png",
        )

        # Components (use full future dataframe for component viz)
        full_future = model.model.make_future_dataframe(periods=0)  # In-sample only
        if args.include_regressors:
            for col in regressor_cols:
                if col in train_df.columns:
                    full_future[col] = train_df[col].values
        full_forecast = model.model.predict(full_future)
        components = model.get_components(full_forecast)

        plot_components(
            components_df=components,
            title=f"Prophet Components (Run: {run_id})",
            save_path=settings.plots_dir / f"components_{run_id}.png",
        )

        # Day-of-week performance
        if "dow_breakdown" in metrics:
            plot_dow_performance(
                dow_metrics=metrics["dow_breakdown"],
                title=f"Day-of-Week Performance (Run: {run_id})",
                save_path=settings.plots_dir / f"dow_performance_{run_id}.png",
            )

        logger.info("Plots saved to %s", settings.plots_dir)

    # --- Step 8: Save Artifacts ---
    logger.info("\n[Step 8] Saving artifacts...")

    # Save metrics JSON
    metrics_file = settings.metrics_dir / f"daily_prophet_metrics_{run_id}.json"
    with open(metrics_file, "w") as f:
        json.dump(
            {
                "run_id": run_id,
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "test_days": args.test_days,
                    "interval_width": args.interval_width,
                    "regressor_type": args.regressor_type,
                    "weekly_seasonality": args.weekly_seasonality,
                    "yearly_seasonality": args.yearly_seasonality,
                    "changepoint_prior_scale": args.changepoint_prior_scale,
                    "seasonality_prior_scale": args.seasonality_prior_scale,
                    "seasonality_mode": args.seasonality_mode,
                },
                "metrics": metrics,
                "baselines": baseline_metrics,
                "comparison": comparison,
            },
            f,
            indent=2,
            default=str,
        )
    logger.info("Metrics saved to %s", metrics_file)

    # Save forecast CSV
    forecast_file = settings.artifacts_dir / f"daily_prophet_forecast_{run_id}.csv"
    test_pred.to_csv(forecast_file, index=False)
    logger.info("Forecast saved to %s", forecast_file)

    # Save model
    model_file = settings.artifacts_dir / f"daily_prophet_model_{run_id}.pkl"
    model.save_model(
        model_file,
        metadata={
            "run_id": run_id,
            "train_days": len(train_df),
            "test_days": len(test_df),
            "test_mae": metrics["mae"],
            "test_rmse": metrics["rmse"],
        },
    )
    logger.info("Model saved to %s", model_file)

    # --- Step 9: Summary Report ---
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1 BASELINE RESULTS SUMMARY")
    logger.info("=" * 80)
    logger.info("\nModel Configuration:")
    logger.info("  Training days: %d", len(train_df))
    logger.info("  Test days: %d", len(test_df))
    logger.info("  Regressors: %s", args.regressor_type if args.include_regressors else "None")
    logger.info("  Weekly seasonality: %s", args.weekly_seasonality)
    logger.info("  Yearly seasonality: %s", args.yearly_seasonality)

    logger.info("\nTest Set Performance:")
    logger.info("  MAE:      %.2f", metrics["mae"])
    logger.info("  RMSE:     %.2f", metrics["rmse"])
    logger.info("  sMAPE:    %.2f%%", metrics["smape"])
    logger.info("  Bias:     %.2f", metrics["bias"])
    logger.info("  R²:       %.4f", metrics["r2"])
    logger.info("  Coverage: %.1f%%", metrics.get("coverage_percent", 0))

    logger.info("\nComparison to Baselines:")
    for baseline_name, baseline_vals in baseline_metrics.items():
        improvement_key = f"vs_{baseline_name}"
        improvement = comparison["improvements"][improvement_key]
        logger.info(
            "  %s: %.2f MAE (%.1f%% %s)",
            baseline_name,
            baseline_vals["mae"],
            abs(improvement["improvement_pct"]),
            "improvement" if improvement["is_better"] else "worse",
        )

    logger.info("\nComparison to Champion:")
    champion_comp = comparison["improvements"]["vs_champion"]
    logger.info(
        "  AutoARIMA: %.2f MAE (%.1f%% %s)",
        comparison["champion_mae"],
        abs(champion_comp["improvement_pct"]),
        "improvement" if champion_comp["is_better"] else "worse",
    )

    # Success criteria
    logger.info("\n" + "=" * 80)
    logger.info("SUCCESS CRITERIA CHECK")
    logger.info("=" * 80)

    seasonal_naive_mae = baseline_metrics.get("seasonal_naive", {}).get("mae", 999)
    beats_seasonal_naive = metrics["mae"] < seasonal_naive_mae
    within_10pct_champion = abs(champion_comp["improvement_pct"]) <= 10
    coverage_ok = 75 <= metrics.get("coverage_percent", 0) <= 85

    logger.info("  Beat seasonal naive (MAE < %.2f): %s", seasonal_naive_mae, "✅ PASS" if beats_seasonal_naive else "❌ FAIL")
    logger.info("  Within 10%% of champion: %s", "✅ PASS" if within_10pct_champion else "❌ FAIL")
    logger.info("  Coverage 75-85%%: %s", "✅ PASS" if coverage_ok else "❌ FAIL")

    logger.info("\n" + "=" * 80)
    logger.info("Artifacts saved with run_id: %s", run_id)
    logger.info("=" * 80 + "\n")


if __name__ == "__main__":
    main()
