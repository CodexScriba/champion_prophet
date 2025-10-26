# Champion Baselines

Reference metrics needed during Phase 0 to judge Prophet progress.

## AutoARIMA Champion (v2.1)

- Cross-validated MAE: **33.66**
- Cross-validated RMSE: **55.71**
- Bias (after calibration): **~0.00**
- Coverage (80% interval): **76.8%**
- Horizon: **14 days**
- Training window: **154 days** (2025-05-18 → 2025-10-23)
- Validation: **4-fold expanding window**
- Regressors: DOW one-hot (Mon–Sat), `is_holiday`, `pre_holiday`, `post_holiday`

Artifacts live under `artifacts/metrics/` with run manifest timestamp
`20251025_064255`.

## Naive Baselines

| Baseline | MAE | RMSE |
| --- | --- | --- |
| Seasonal naive (7-day lag) | 38.00 | 71.34 |
| Moving average (7-day) | 116.11 | 130.08 |

Use these as minimum performance targets for any Prophet challenger.
