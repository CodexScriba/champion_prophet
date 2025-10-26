"""Plotting utilities for Prophet forecast visualization.

This module provides functions to create standard forecast plots including
forecast vs actuals, components, residuals, and day-of-week analyses.
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def plot_forecast_vs_actual(
    dates: pd.Series,
    y_true: pd.Series | np.ndarray,
    y_pred: pd.Series | np.ndarray,
    y_lower: pd.Series | np.ndarray | None = None,
    y_upper: pd.Series | np.ndarray | None = None,
    train_end_date: pd.Timestamp | None = None,
    title: str = "Prophet Forecast vs Actual",
    save_path: Path | str | None = None,
) -> None:
    """Plot forecast against actual values with optional prediction intervals.

    Args:
        dates: Date column
        y_true: Actual values
        y_pred: Predicted values
        y_lower: Lower bound of prediction interval (optional)
        y_upper: Upper bound of prediction interval (optional)
        train_end_date: Date where training ends (draws vertical line)
        title: Plot title
        save_path: Path to save figure (if None, displays instead)
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot actual values
    ax.plot(dates, y_true, "o-", label="Actual", color="black", linewidth=1.5, markersize=4)

    # Plot forecast
    ax.plot(dates, y_pred, "s--", label="Forecast", color="#1f77b4", linewidth=1.5, markersize=3, alpha=0.8)

    # Plot prediction intervals if provided
    if y_lower is not None and y_upper is not None:
        ax.fill_between(dates, y_lower, y_upper, alpha=0.2, color="#1f77b4", label="80% Prediction Interval")

    # Mark train/test split
    if train_end_date is not None:
        ax.axvline(train_end_date, color="red", linestyle="--", linewidth=2, label="Train/Test Split")

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Email Volume", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    plt.xticks(rotation=45)
    plt.tight_layout()

    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info("Saved forecast plot to %s", save_path)
        plt.close()
    else:
        plt.show()


def plot_residuals(
    dates: pd.Series,
    y_true: pd.Series | np.ndarray,
    y_pred: pd.Series | np.ndarray,
    title: str = "Forecast Residuals",
    save_path: Path | str | None = None,
) -> None:
    """Plot forecast residuals (actual - predicted).

    Args:
        dates: Date column
        y_true: Actual values
        y_pred: Predicted values
        title: Plot title
        save_path: Path to save figure (if None, displays instead)
    """
    residuals = np.asarray(y_true) - np.asarray(y_pred)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Time series of residuals
    axes[0, 0].plot(dates, residuals, "o-", color="darkred", linewidth=1, markersize=3)
    axes[0, 0].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[0, 0].set_xlabel("Date")
    axes[0, 0].set_ylabel("Residual (Actual - Predicted)")
    axes[0, 0].set_title("Residuals Over Time")
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].tick_params(axis="x", rotation=45)

    # Histogram of residuals
    axes[0, 1].hist(residuals, bins=20, color="darkred", alpha=0.7, edgecolor="black")
    axes[0, 1].axvline(0, color="black", linestyle="--", linewidth=1)
    axes[0, 1].set_xlabel("Residual")
    axes[0, 1].set_ylabel("Frequency")
    axes[0, 1].set_title(f"Residual Distribution (Mean={np.mean(residuals):.2f})")
    axes[0, 1].grid(True, alpha=0.3)

    # Q-Q plot
    from scipy import stats

    stats.probplot(residuals, dist="norm", plot=axes[1, 0])
    axes[1, 0].set_title("Q-Q Plot (Normal)")
    axes[1, 0].grid(True, alpha=0.3)

    # Residuals vs predicted
    axes[1, 1].scatter(y_pred, residuals, alpha=0.6, color="darkred", s=30)
    axes[1, 1].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[1, 1].set_xlabel("Predicted Value")
    axes[1, 1].set_ylabel("Residual")
    axes[1, 1].set_title("Residuals vs Predicted")
    axes[1, 1].grid(True, alpha=0.3)

    plt.suptitle(title, fontsize=14, fontweight="bold", y=1.00)
    plt.tight_layout()

    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info("Saved residuals plot to %s", save_path)
        plt.close()
    else:
        plt.show()


def plot_components(
    components_df: pd.DataFrame,
    title: str = "Prophet Forecast Components",
    save_path: Path | str | None = None,
) -> None:
    """Plot Prophet forecast components (trend, seasonality, etc.).

    Args:
        components_df: DataFrame with ds, trend, weekly, etc.
        title: Plot title
        save_path: Path to save figure (if None, displays instead)
    """
    # Determine which components are present
    has_trend = "trend" in components_df.columns
    has_weekly = "weekly" in components_df.columns
    has_yearly = "yearly" in components_df.columns

    # Count non-date columns
    n_plots = sum([has_trend, has_weekly, has_yearly])

    if n_plots == 0:
        logger.warning("No components found to plot")
        return

    fig, axes = plt.subplots(n_plots, 1, figsize=(14, 4 * n_plots))

    if n_plots == 1:
        axes = [axes]

    idx = 0

    # Plot trend
    if has_trend:
        axes[idx].plot(components_df["ds"], components_df["trend"], color="darkblue", linewidth=2)
        axes[idx].set_xlabel("Date")
        axes[idx].set_ylabel("Trend")
        axes[idx].set_title("Trend Component")
        axes[idx].grid(True, alpha=0.3)
        axes[idx].tick_params(axis="x", rotation=45)
        idx += 1

    # Plot weekly seasonality
    if has_weekly:
        axes[idx].plot(components_df["ds"], components_df["weekly"], color="darkgreen", linewidth=2)
        axes[idx].set_xlabel("Date")
        axes[idx].set_ylabel("Weekly")
        axes[idx].set_title("Weekly Seasonality Component")
        axes[idx].grid(True, alpha=0.3)
        axes[idx].tick_params(axis="x", rotation=45)
        idx += 1

    # Plot yearly seasonality
    if has_yearly:
        axes[idx].plot(components_df["ds"], components_df["yearly"], color="darkorange", linewidth=2)
        axes[idx].set_xlabel("Date")
        axes[idx].set_ylabel("Yearly")
        axes[idx].set_title("Yearly Seasonality Component")
        axes[idx].grid(True, alpha=0.3)
        axes[idx].tick_params(axis="x", rotation=45)

    plt.suptitle(title, fontsize=14, fontweight="bold", y=1.00)
    plt.tight_layout()

    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info("Saved components plot to %s", save_path)
        plt.close()
    else:
        plt.show()


def plot_dow_performance(
    dow_metrics: dict[str, dict[str, float]],
    title: str = "Day-of-Week Performance",
    save_path: Path | str | None = None,
) -> None:
    """Plot day-of-week performance metrics.

    Args:
        dow_metrics: Dictionary from calculate_dow_metrics
        title: Plot title
        save_path: Path to save figure (if None, displays instead)
    """
    dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # Extract metrics
    maes = [dow_metrics.get(day, {}).get("mae", np.nan) for day in dow_names]
    biases = [dow_metrics.get(day, {}).get("bias", np.nan) for day in dow_names]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # MAE by day of week
    axes[0].bar(dow_names, maes, color="steelblue", alpha=0.7, edgecolor="black")
    axes[0].set_xlabel("Day of Week")
    axes[0].set_ylabel("MAE")
    axes[0].set_title("MAE by Day of Week")
    axes[0].grid(True, alpha=0.3, axis="y")
    axes[0].tick_params(axis="x", rotation=45)

    # Bias by day of week
    colors = ["red" if b > 0 else "green" for b in biases]
    axes[1].bar(dow_names, biases, color=colors, alpha=0.7, edgecolor="black")
    axes[1].axhline(0, color="black", linestyle="--", linewidth=1)
    axes[1].set_xlabel("Day of Week")
    axes[1].set_ylabel("Bias (Positive = Over-forecast)")
    axes[1].set_title("Bias by Day of Week")
    axes[1].grid(True, alpha=0.3, axis="y")
    axes[1].tick_params(axis="x", rotation=45)

    plt.suptitle(title, fontsize=14, fontweight="bold")
    plt.tight_layout()

    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info("Saved DOW performance plot to %s", save_path)
        plt.close()
    else:
        plt.show()
