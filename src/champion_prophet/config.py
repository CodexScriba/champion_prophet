"""Shared configuration utils for Prophet experimentation.

The goal is to reuse consistent paths, logging, and random seed
initialisation across notebooks and scripts.
"""

from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "database" / "email_database.db"
DEFAULT_ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"

ENV_DATABASE_PATH = "PROPHET_DATABASE_PATH"
ENV_ARTIFACTS_DIR = "PROPHET_ARTIFACTS_DIR"
ENV_RANDOM_SEED = "PROPHET_RANDOM_SEED"


def _env_path(name: str, default: Path) -> Path:
    """Return a `Path` from an environment variable when present."""

    override = os.getenv(name)
    return Path(override).expanduser() if override else default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:  # pragma: no cover - defensive branch
        raise ValueError(f"Environment variable {name} must be an integer") from exc


@dataclass(slots=True)
class Settings:
    """Runtime configuration for Prophet experiments."""

    database_path: Path = field(default_factory=lambda: _env_path(ENV_DATABASE_PATH, DEFAULT_DB_PATH))
    artifacts_dir: Path = field(default_factory=lambda: _env_path(ENV_ARTIFACTS_DIR, DEFAULT_ARTIFACTS_DIR))
    plots_dir: Path = field(init=False)
    metrics_dir: Path = field(init=False)
    logs_dir: Path = field(default_factory=lambda: DEFAULT_LOG_DIR)
    forecast_horizon_days: int = 14
    coverage_target: float = 0.80
    random_seed: int = field(default_factory=lambda: _env_int(ENV_RANDOM_SEED, 42))

    def derived_paths(self) -> Iterable[Path]:
        return (self.artifacts_dir, self.plots_dir, self.metrics_dir, self.logs_dir)

    def __post_init__(self) -> None:
        object.__setattr__(self, "plots_dir", self.artifacts_dir / "plots")
        object.__setattr__(self, "metrics_dir", self.artifacts_dir / "metrics")


def load_settings() -> Settings:
    """Load settings from environment overrides and defaults."""

    return Settings()


def ensure_directories(settings: Settings) -> None:
    """Ensure commonly used directories exist before IO-heavy steps."""

    for path in settings.derived_paths():
        path.mkdir(parents=True, exist_ok=True)


def set_global_seed(seed: int) -> None:
    """Seed Python, NumPy, and Prophet-compatible generators."""

    random.seed(seed)
    np.random.seed(seed)
    try:  # torch is optional but used by some downstream tools
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():  # pragma: no cover - depends on runtime
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def configure_logging(level: str | int | None = None) -> None:
    """Initialise structured logging with an overridable level."""

    log_level = level or os.getenv("PROPHET_LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.captureWarnings(True)
