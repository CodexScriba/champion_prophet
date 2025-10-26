from __future__ import annotations

import numpy as np

from evaluation.metrics import calculate_baseline_metrics


def test_baseline_metrics_respect_evaluation_window() -> None:
    y_true = np.array([10, 12, 14, 16, 18, 20, 22, 24, 26])
    evaluation_start = 7  # last two observations treated as hold-out

    baselines = calculate_baseline_metrics(
        y_true=y_true,
        dates=None,
        evaluation_start_index=evaluation_start,
        seasonal_period=7,
    )

    seasonal = baselines["seasonal_naive"]
    # Expected predictions: index7 -> y0 (10), index8 -> y1 (12)
    expected_mae = (abs(24 - 10) + abs(26 - 12)) / 2
    assert np.isclose(seasonal["mae"], expected_mae)

    moving_avg = baselines["moving_average_7"]
    assert moving_avg["mae"] >= 0
