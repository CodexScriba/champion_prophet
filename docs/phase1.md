# Phase 1 Implementation Summary (Prophet Daily Baseline)

**Phase:** 1 – Baseline Daily Model  
**Latest Run ID:** `20251026_130816`  
**Status:** ✅ Complete (baseline in place, gaps documented)  
**Last Updated:** 2025-10-26

---

## Objectives Recap

1. Stand up reusable daily data loader returning Prophet-ready frames.  
2. Provide a thin Prophet wrapper with artifact persistence.  
3. Produce a scripted baseline run with metrics, plots, and documentation.  
4. Benchmark Prophet vs. naive baselines and AutoARIMA champion.  
5. Capture lessons / gaps to drive Phase 2 cross-validation work.

All objectives remain satisfied after regenerating artifacts against the refreshed database.

---

## Source Code & Assets

| Area | Path | Notes |
| --- | --- | --- |
| **Config** | `src/champion_prophet/config.py` | Shared paths, logging, seed handling (pre-existing). |
| **Data** | `src/data/daily_loader.py` | Loads `total_emails`, handles null filtering, creates Prophet frame. Review fix: day-of-week one-hot creation now drops Sunday correctly and preserves deterministic column order. |
| **Model** | `src/models/prophet_daily.py` | Wrapper around `prophet.Prophet` with regressor support, persistence helpers. |
| **Evaluation** | `src/evaluation/metrics.py`, `src/evaluation/plots.py` | Metric suite and diagnostic plots. Review fix: naive baselines now evaluate on the designated hold-out slice (no leakage from training window). |
| **Runner** | `scripts/run_prophet_daily.py` | CLI orchestration (load → split → fit → evaluate → save). Review fix: defaults target `total_emails`, wires updated baseline evaluation index, retains timestamped artifacts. |
| **Documentation** | `docs/prophet_daily_baseline.md`, `docs/phase1.md` | Updated with regenerated run results and findings. |

---

## Artifact Regeneration

- Removed legacy artifacts from prior runs (`artifacts/` cleared).  
- Re-ran `scripts/run_prophet_daily.py` using the repaired database (no nulls in `total_emails`).  
- Generated fresh metrics, plots, and serialized model under run ID `20251026_130816`.  
- See `docs/prophet_daily_baseline.md` for the full narrative and artifact manifest.

---

## Baseline Evaluation (Hold-out: 2025-10-11 → 2025-10-24)

| Metric | Value | Comment |
| --- | --- | --- |
| **MAE** | **44.75** | Prophet trails seasonal naive (38.64) and champion (33.66). |
| **RMSE** | 63.39 | Directional only. |
| **sMAPE** | 40.93% | High variance around actuals. |
| **Bias** | −22.41 | Consistent under-forecasting; Monday/Thursday worst offenders. |
| **Coverage (80% PI)** | 85.7% | Slightly above 75–85% guardrail (over-confident interval width). |

Baseline comparison (test window only):
- Seasonal naive: MAE 38.64 → Prophet is 15.8% worse (❌).  
- 7-day moving average: MAE 115.67 → Prophet 61.3% better (✅).  
- Champion AutoARIMA: MAE 33.66 → Prophet 32.9% worse (❌).

Day-of-week diagnostic highlights (n=2 per day):
- Monday MAE 97.6 (−97.6 bias); Thursday MAE 69.5 → deep under-forecasting.  
- Saturday MAE 58.5 (+58.5 bias) → over-forecast persists despite longer history.  
- Tuesday and Sunday show smaller absolute errors but retain directional bias.

---

## Key Findings

1. **Trend Flexibility:** Default `changepoint_prior_scale=0.05` still underfits the late-period ramp, yielding negative bias.  
2. **Feature Gap:** Weekend heuristic regressors are insufficient; DOW one-hot columns should now be exercised (bug fix unblocks Phase 2 experiments).  
3. **Coverage Overshoot:** Hold-out coverage sits above guardrail (85.7%). Interval calibration is required even at baseline.  
4. **Data Quality:** `total_emails` is now fully populated (155 consecutive days), eliminating earlier blockers and aligning with champion dataset.

---

## Improvements Added During Review

- Corrected DOW regressor generation to drop Sunday cleanly and maintain stable column ordering.  
- Adjusted baseline metrics to evaluate strictly on the hold-out window, preventing optimistic comparisons.  
- Switched default target to `total_emails`, leveraging the repaired database and mirroring champion inputs.  
- Regenerated documentation and artifacts to reflect the latest dataset and metrics.

---

## Phase 2 Prep – Recommended Next Actions

1. **Expanding-Window Cross-Validation:** Reproduce champion protocol (minimum 56-day train, 14-day horizon, ≥4 folds).  
2. **Hyperparameter Sweep:** Explore grid over `changepoint_prior_scale`, `seasonality_prior_scale`, and `seasonality_mode` (add multiplicative option).  
3. **Feature Enhancements:** Activate DOW regressors, test proper holiday calendars, and consider lag-based features for Monday recovery.  
4. **Calibration Framework:** Begin bias correction (per-DOW adjustments) and interval scaling to target 75–85% coverage.  
5. **Testing Infrastructure:** Introduce pytest coverage for loaders, metrics, and serialization to lock in recent fixes before iteration.

Baselines and documentation are now aligned with the latest database. Phase 2 cross-validation, tuning, and first-pass calibration live in `docs/prophet_phase2.md`.
