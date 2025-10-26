# Prophet Architecture & Roadmap

**Primary Goal:** Deliver a Prophet-based forecasting pipeline that decisively outperforms the reigning AutoARIMA champion across all champion criteria (MAE, RMSE, coverage, bias, production readiness).

---

## Strategic Pillars
- **Model Accuracy:** Tune Prophet components (trend, weekly/holiday seasonality, custom regressors) to match the 154-day training window and 4-fold expanding CV protocol.
- **Calibration Discipline:** Apply day-of-week bias corrections and interval scaling to land 80% coverage inside the 75–85% guard rails.
- **Operational Parity:** Mirror champion automation—Makefile targets, run manifests, artifact storage, and guard rails—to earn promotion readiness.
- **Auditability:** Produce reproducible artifacts (metrics JSON, CV backtests, calibrated forecasts, serialized models) and document each run.

---

## System Blueprint
1. **Data Layer**
   - Source: `database/email_database.db` / `.json`
   - Interface: shared data loaders that expose daily totals plus holiday & DOW regressors
2. **Feature Engineering**
   - Prophet holidays with `is_holiday`, `pre_holiday`, `post_holiday`
   - Weekly seasonality + optional DOW one-hots for residual structure
3. **Training Orchestrator**
   - Script: `scripts/run_daily_prophet.py` (planned)
   - Responsibilities: align folds with champion splits, log configs, emit manifests
4. **Calibration Module**
   - Applies DOW bias offsets and interval scaling derived from CV residuals
5. **Evaluation Suite**
   - Metrics: MAE, RMSE, sMAPE, bias, coverage, R²
   - Baselines: seasonal naive, MA7, AutoARIMA champion
6. **Artifacts & Reporting**
   - Storage under `artifacts/` with timestamped folders
   - Comparative report: `reports/prophet_vs_champion.md`

---

## Success Criteria Checklist
- MAE < 38.00 and <116.11 (beats naive & MA7 baselines)
- MAE within ±10% of champion (≤37.03) or better
- Coverage between 75% and 85%
- Post-calibration bias ≈ 0 across days of week
- Full artifact package + automation hooks ready for CI

---

## Immediate Next Steps
1. Implement Prophet runner module and CLI harness.
2. Reuse CV splitter from AutoARIMA pipeline for apples-to-apples metrics.
3. Stand up calibration notebook/script to derive DOW adjustments.
4. Generate first CV report and compare against champion metrics.
