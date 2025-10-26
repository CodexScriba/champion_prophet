"""Prophet model wrapper for daily email volume forecasting.

This module provides a high-level interface for training and forecasting
with Prophet, including support for custom regressors and artifact persistence.
"""

from __future__ import annotations

import json
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from prophet import Prophet

logger = logging.getLogger(__name__)


class ProphetDailyModel:
    """Wrapper for Prophet daily forecasting with email volume data.

    This class encapsulates Prophet configuration, training, prediction,
    and artifact serialization for daily email volume forecasts.

    Attributes:
        model: The underlying Prophet model instance
        config: Configuration dictionary for the model
        is_fitted: Whether the model has been fitted to data
        regressor_names: List of custom regressor names added to the model
    """

    def __init__(
        self,
        interval_width: float = 0.80,
        weekly_seasonality: bool = True,
        yearly_seasonality: bool = False,
        daily_seasonality: bool = False,
        changepoint_prior_scale: float = 0.05,
        seasonality_prior_scale: float = 10.0,
        seasonality_mode: str = "additive",
        growth: str = "linear",
    ):
        """Initialize Prophet model with configuration.

        Args:
            interval_width: Width of uncertainty intervals (default: 0.80 for 80% PI)
            weekly_seasonality: Enable weekly seasonality (default: True)
            yearly_seasonality: Enable yearly seasonality (default: False)
            daily_seasonality: Enable daily seasonality (default: False)
            changepoint_prior_scale: Flexibility of trend changes (default: 0.05)
            seasonality_prior_scale: Strength of seasonality (default: 10.0)
            seasonality_mode: "additive" or "multiplicative" (default: "additive")
            growth: "linear" or "logistic" (default: "linear")
        """
        self.config = {
            "interval_width": interval_width,
            "weekly_seasonality": weekly_seasonality,
            "yearly_seasonality": yearly_seasonality,
            "daily_seasonality": daily_seasonality,
            "changepoint_prior_scale": changepoint_prior_scale,
            "seasonality_prior_scale": seasonality_prior_scale,
            "seasonality_mode": seasonality_mode,
            "growth": growth,
        }

        self.model = Prophet(**self.config)
        self.is_fitted = False
        self.regressor_names: list[str] = []

        logger.info("Initialized ProphetDailyModel with config: %s", self.config)

    def add_regressors(self, regressor_names: list[str]) -> None:
        """Add custom regressors to the model.

        Must be called before fitting.

        Args:
            regressor_names: List of column names to use as regressors
        """
        if self.is_fitted:
            raise RuntimeError("Cannot add regressors after model is fitted")

        for name in regressor_names:
            self.model.add_regressor(name)
            self.regressor_names.append(name)
            logger.debug("Added regressor: %s", name)

        logger.info("Added %d regressors to model", len(regressor_names))

    def fit(self, train_df: pd.DataFrame) -> ProphetDailyModel:
        """Fit the Prophet model to training data.

        Args:
            train_df: DataFrame with columns 'ds', 'y', and any regressors

        Returns:
            Self for method chaining

        Raises:
            ValueError: If required columns are missing
        """
        required_cols = {"ds", "y"}
        if not required_cols.issubset(train_df.columns):
            missing = required_cols - set(train_df.columns)
            raise ValueError(f"Missing required columns: {missing}")

        # Verify regressors are present
        for reg in self.regressor_names:
            if reg not in train_df.columns:
                raise ValueError(f"Regressor '{reg}' not found in training data")

        logger.info("Fitting Prophet model on %d training samples", len(train_df))
        logger.debug("Training date range: %s to %s", train_df["ds"].min(), train_df["ds"].max())

        self.model.fit(train_df)
        self.is_fitted = True

        logger.info("Model training completed successfully")
        return self

    def predict(self, periods: int | None = None, future_df: pd.DataFrame | None = None) -> pd.DataFrame:
        """Generate forecasts.

        Args:
            periods: Number of periods to forecast (if future_df not provided)
            future_df: Pre-built future DataFrame (if provided, periods is ignored)

        Returns:
            DataFrame with columns ds, yhat, yhat_lower, yhat_upper, and components

        Raises:
            RuntimeError: If model hasn't been fitted
            ValueError: If neither periods nor future_df is provided
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")

        if future_df is None:
            if periods is None:
                raise ValueError("Must provide either periods or future_df")

            logger.info("Making future dataframe for %d periods", periods)
            future_df = self.model.make_future_dataframe(periods=periods)

            # Add regressors with zeros (placeholder - caller should set properly)
            for reg in self.regressor_names:
                if reg not in future_df.columns:
                    future_df[reg] = 0
                    logger.warning(
                        "Regressor '%s' not in future_df, filled with zeros. "
                        "Caller should provide proper values.",
                        reg,
                    )

        logger.info("Generating forecast for %d periods", len(future_df))
        forecast = self.model.predict(future_df)

        return forecast

    def forecast_holdout(self, test_df: pd.DataFrame) -> pd.DataFrame:
        """Generate forecasts for a held-out test set.

        This is useful for backtesting where you have actual future data
        with regressor values.

        Args:
            test_df: DataFrame with 'ds' and regressor columns

        Returns:
            Forecast DataFrame aligned with test_df dates
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")

        # Verify regressors are present in test data
        for reg in self.regressor_names:
            if reg not in test_df.columns:
                raise ValueError(f"Regressor '{reg}' not found in test data")

        logger.info("Forecasting holdout period: %d days", len(test_df))
        forecast = self.model.predict(test_df)

        return forecast

    def save_model(self, path: Path | str, metadata: dict[str, Any] | None = None) -> None:
        """Serialize model to disk.

        Args:
            path: File path to save the model (will create .pkl file)
            metadata: Optional metadata to save alongside model
        """
        if not self.is_fitted:
            logger.warning("Saving unfitted model")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Create save bundle
        save_obj = {
            "model": self.model,
            "config": self.config,
            "regressors": self.regressor_names,
            "is_fitted": self.is_fitted,
            "metadata": metadata or {},
            "saved_at": datetime.now().isoformat(),
        }

        with open(path, "wb") as f:
            pickle.dump(save_obj, f)

        logger.info("Model saved to %s", path)

        # Save config as JSON for human readability
        config_path = path.with_suffix(".json")
        with open(config_path, "w") as f:
            json.dump(
                {
                    "config": self.config,
                    "regressors": self.regressor_names,
                    "is_fitted": self.is_fitted,
                    "metadata": metadata or {},
                    "saved_at": save_obj["saved_at"],
                },
                f,
                indent=2,
            )
        logger.debug("Model config saved to %s", config_path)

    @classmethod
    def load_model(cls, path: Path | str) -> ProphetDailyModel:
        """Load a serialized model from disk.

        Args:
            path: File path to the saved model (.pkl file)

        Returns:
            Loaded ProphetDailyModel instance
        """
        path = Path(path)

        with open(path, "rb") as f:
            save_obj = pickle.load(f)

        # Reconstruct model instance
        instance = cls.__new__(cls)
        instance.model = save_obj["model"]
        instance.config = save_obj["config"]
        instance.regressor_names = save_obj["regressors"]
        instance.is_fitted = save_obj["is_fitted"]

        logger.info(
            "Model loaded from %s (saved at %s)",
            path,
            save_obj.get("saved_at", "unknown"),
        )

        return instance

    def get_components(self, forecast: pd.DataFrame) -> pd.DataFrame:
        """Extract forecast components (trend, seasonality, etc.).

        Args:
            forecast: Forecast DataFrame from predict()

        Returns:
            DataFrame with date and component columns
        """
        component_cols = ["ds", "trend"]

        # Add weekly seasonality if enabled
        if self.config["weekly_seasonality"] and "weekly" in forecast.columns:
            component_cols.append("weekly")

        # Add yearly seasonality if enabled
        if self.config["yearly_seasonality"] and "yearly" in forecast.columns:
            component_cols.append("yearly")

        # Add regressor effects
        for reg in self.regressor_names:
            if reg in forecast.columns:
                component_cols.append(reg)

        return forecast[component_cols].copy()
