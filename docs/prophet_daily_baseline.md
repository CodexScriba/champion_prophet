# Prophet Daily Baseline – Phase 1 Results

**Run ID:** 20251026_130816  
**Run Date:** 2025-10-26  
**Authoring Script:** `scripts/run_prophet_daily.py`

---

## Executive Summary

- Baseline Prophet model on `total_emails` delivers **MAE 44.75**, **RMSE 63.39**, **sMAPE 40.93%**, and **bias −22.41** on a 14-day hold-out.  
- Seasonal naive remains ahead (MAE 38.64), while Prophet comfortably beats the 7-day moving average baseline (MAE 115.67).  
- Coverage at the configured 80% interval lands at **85.7%**, slightly above the 75–85% target band; interval calibration still required.  
- Day-of-week errors continue to show strong under-forecasting during weekdays (e.g., Monday MAE 97.61) and mixed behaviour on weekends.  
- The refreshed database eliminates prior null issues in `total_emails`, enabling parity with champion data handling.

---

## Data & Configuration

- **Database:** `database/email_database.db` (post-fix, 155 valid days from 2025-05-18 through 2025-10-24)  
- **Target column:** `total_emails`  
- **Train window:** 141 days (2025-05-18 → 2025-10-10)  
- **Test window:** 14 days (2025-10-11 → 2025-10-24)  
- **Regressors:** weekend heuristic (`is_holiday`, `pre_holiday`, `post_holiday`)  
  - DOW one-hot regressors (`dow_0`…`dow_5`) are wired into the data loader and leveraged in the Phase 2 tooling; this baseline run intentionally omitted them.
- **Prophet config:** `interval_width=0.80`, `changepoint_prior_scale=0.05`, `seasonality_prior_scale=10.0`, `seasonality_mode='additive'`, weekly seasonality enabled

---

## Hold-out Metrics (14 days)

| Metric | Value | Target / Comment | Status |
| --- | --- | --- | --- |
| **MAE** | **44.75** | Beat seasonal naive (≤38.64) | ❌ |
| **RMSE** | 63.39 | Informational | - |
| **sMAPE** | 40.93% | lower is better | - |
| **Bias** | −22.41 | Aim for ≈0 | ❌ |
| **R²** | 0.766 | Directional | ⚠️ |
| **Coverage (80% PI)** | **85.7%** | Target 75–85% | ⚠️ (high) |

Baselines are evaluated on the same 14-day window:

| Baseline | MAE | RMSE | Bias | Prophet vs Baseline |
| --- | --- | --- | --- | --- |
| **Seasonal Naive (lag 7)** | 38.64 | 59.86 | −10.21 | 15.8% worse ❌ |
| **Moving Average (7-day)** | 115.67 | 130.09 | −8.08 | 61.3% better ✅ |
| **AutoARIMA Champion** | 33.66 | 55.71 | ≈0 | 32.9% worse ❌ |

---

## Day-of-Week Breakdown

| Day | MAE | Bias | Samples | Notes |
| --- | --- | --- | --- | --- |
| Monday | 97.61 | −97.61 | 2 | Largest under-forecast |
| Tuesday | 12.25 | −8.18 | 2 | Best weekday |
| Wednesday | 35.75 | −28.31 | 2 | Moderate under-forecast |
| Thursday | 69.51 | −69.51 | 2 | Still severe under-forecast |
| Friday | 29.84 | −2.32 | 2 | Near unbiased |
| Saturday | 58.52 | +58.52 | 2 | Over-forecast persists |
| Sunday | 9.75 | −9.47 | 2 | Small errors but biased |

**Takeaways**
- Weekday under-forecasting worsens with the longer history now available in `total_emails`.
- Weekend heuristic remains insufficient; richer calendar or DOW regressors needed.

---

## Diagnostics

- **Bias:** −22.41 → tighter changepoint or multiplicative seasonality may help capture post-summer ramp.  
- **Coverage:** 85.7% (>85% goal). Calibration should widen/shift intervals more surgically rather than blanket scaling.  
- **Residual plots:** heavy negative residuals concentrated early week; positive spikes on Saturday.  
- **Components:** trend still linear with mild upward slope; weekly component insufficiently sharp for Monday/Thursday peaks.

---

## Generated Artifacts (`run_id=20251026_130816`)

- `artifacts/daily_prophet_forecast_20251026_130816.csv` – hold-out predictions with actuals  
- `artifacts/daily_prophet_model_20251026_130816.pkl` (+`.json`) – serialized model + metadata  
- `artifacts/metrics/daily_prophet_metrics_20251026_130816.json` – metrics, baselines, comparisons  
- `artifacts/plots/forecast_vs_actual_20251026_130816.png`  
- `artifacts/plots/residuals_20251026_130816.png`  
- `artifacts/plots/components_20251026_130816.png`  
- `artifacts/plots/dow_performance_20251026_130816.png`

---

## Next Steps Toward Phase 2

1. Introduce DOW one-hot regressors (bugfix already landed in loader) and reassess baseline parity.  
2. Launch grid search over `changepoint_prior_scale` and `seasonality_mode` using expanding-window CV.  
3. Begin bias/interval calibration workflow to bring bias toward 0 and coverage into the 75–85% band.  
4. Add lightweight unit tests for loader/metrics to lock in recent fixes (evaluation window handling, DOW regressors).
