# Prophet Phase 2 – CV, Tuning, and Calibration (Run 20251026_131838)

**Objective:** Execute the Phase 2 plan: add richer regressors, reproduce champion-style expanding-window CV, run a compact hyperparameter search, and derive first-pass calibration parameters using the refreshed database (155 days of `total_emails`).

---

## Workflow Overview

| Step | Details |
| --- | --- |
| **Data** | `total_emails`, 2025-05-18 → 2025-10-24. Prophet frame includes weekend heuristic + DOW one-hot regressors (`dow_0`…`dow_5`). |
| **CV Protocol** | Expanding window with 4 folds, 56-day minimum train, 14-day horizon (mirrors champion). |
| **Grid Search** | `changepoint_prior_scale` ∈ {0.01, 0.05, 0.10}; `seasonality_prior_scale` ∈ {5, 10, 15}; `seasonality_mode` ∈ {additive, multiplicative}. |
| **Calibration** | DOW bias adjustments (50% shrinkage) + interval scaling toward 80% coverage using CV out-of-sample residuals. |
| **Hold-out** | Final 14 days (2025-10-11 → 2025-10-24) reserved for evaluation after retraining on preceding 141 days. |

Artifacts are associated with run ID **20251026_131838** and produced by `scripts/run_prophet_phase2.py`.

---

## Cross-Validation Findings

| Metric | Value |
| --- | --- |
| Best configuration | `changepoint_prior_scale=0.10`, `seasonality_prior_scale=5.0`, `seasonality_mode="multiplicative"` |
| CV folds | 4 (56/14 expanding) |
| CV MAE | 64.67 |
| CV RMSE | 89.13 |
| CV Bias | +7.59 |
| CV Coverage (80% PI) | 69.6% (intervals too narrow) |

**Notes**
- Multiplicative seasonality + smaller seasonality prior delivered the strongest average MAE in spite of early-fold volatility.
- Weekday bias remained positive in CV, reinforcing the need for DOW adjustments.
- Coverage shortfall (≈70%) motivated a modest interval expansion (scale ≈ 1.05).

Full combination results are captured in `artifacts/metrics/prophet_phase2_metrics_20251026_131838.json`.

---

## Calibration Parameters

| Component | Value |
| --- | --- |
| DOW bias (after 0.5 shrinkage) | `{Mon: +56.5, Tue: +12.2, Wed: −0.8, Thu: −3.3, Fri: −15.3, Sat: −75.7, Sun: −0.27}` |
| Interval scale | 1.052 |
| CV coverage | 69.6% |
| Target coverage | 80% |

The adjustments apply additively to Prophet outputs and scale the interval half-width symmetrically.

---

## Hold-out Evaluation (2025-10-11 → 2025-10-24)

### Raw Prophet (Best Config, No Calibration)

| Metric | Value | Champion Δ | Seasonal Naive Δ |
| --- | --- | --- | --- |
| MAE | 40.51 | +6.85 (**worse**) | +1.87 (**worse**) |
| RMSE | 57.69 | +1.98 | −2.16 |
| Bias | +3.50 | +3.50 | — |
| Coverage | 92.9% | Above 85% guardrail |

Pain points remain: Monday under-forecast (bias −73) and Saturday over-forecast (+85). Intervals are already wide (coverage > 90%).

### Calibrated Forecast (Bias + Interval Adjustments)

| Metric | Value | Champion Δ | Seasonal Naive Δ |
| --- | --- | --- | --- |
| **MAE** | **31.36** | **−2.30 (6.8% better)** | **−7.28 (18.8% better)** |
| RMSE | 40.83 | −14.88 | −29.03 |
| Bias | −0.29 | ≈0 | — |
| Coverage | 100% | Still above guardrail (needs tightening) |

Calibration materially improves accuracy (beats champion on MAE) and neutralises overall bias, but coverage overshoots to 100%. Further interval tuning is required to hit the 75–85% band without sacrificing gains.

Day-of-week behaviour post-calibration:
- Monday MAE 70.4 (bias −16.9) – improved vs raw but still heavy variance.
- Saturday MAE 9.53 (bias +9.53) – drastically better after negative bias correction.
- Tuesday bias remains positive (+35) – suggests over-correction, worth moderating shrinkage or adding covariates.

---

## Generated Artifacts (Run 20251026_131838)

- `artifacts/metrics/prophet_phase2_metrics_20251026_131838.json` – CV history, calibration parameters, hold-out comparisons.
- `artifacts/prophet_phase2_forecast_20251026_131838.csv` – Raw & calibrated forecasts with adjustments and interval scale.
- `artifacts/prophet_phase2_cv_predictions_20251026_131838.csv` – Fold-level predictions for deeper diagnostics.
- Plots under `artifacts/plots/`:
  - `phase2_forecast_20251026_131838.png`
  - `phase2_residuals_20251026_131838.png`
  - `phase2_components_20251026_131838.png`
  - `phase2_dow_20251026_131838.png`

---

## Test Coverage

New unit tests ensure:
- DOW regression matrix drops Sunday and remains deterministic (`tests/test_daily_loader.py`).
- Naive baseline comparison respects the hold-out boundary (`tests/test_metrics.py`).

Run via `venv/bin/python -m pytest`.

---

## Next Iteration Recommendations

1. **Interval Calibration Refinement:** Coverage remains too high on hold-out. Consider:
   - Lowering interval gain or learning a separate shrinkage factor per DOW.
   - Distinguishing between weekday/weekend scaling.
   - Validating on additional folds once more history accrues.
2. **Bias Regularisation:** DOW adjustments over-correct Tuesdays; introduce ridge-like shrinkage or regressors capturing business mix.
3. **Feature Experiments:** Lagged demand (y_{t-1}, y_{t-7}), campaign signals, or external drivers may reduce Monday swings.
4. **Automation:** Promote `scripts/run_prophet_phase2.py` into CI to keep artifacts fresh as data grows.

The Phase 2 pipeline is now reproducible, delivers a calibrated forecast that edges past the champion MAE, and lays the groundwork for guardrail tuning in Phase 3.

