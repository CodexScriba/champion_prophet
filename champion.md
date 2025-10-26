# Robostradamus Champion Results - Testing Baseline for Prophet Comparison

**Purpose:** Document best-performing ARIMA and Greykite results to establish a fair baseline for Prophet testing. All models should be tested using the same methodology and data for valid comparison.

**Last Updated:** 2025-10-25

---

## Testing Methodology (To Be Used for All Models)

### Training & Validation Approach
- **Training Window:** 154 days (2025-05-18 to 2025-10-23)
- **Validation Method:** 4-fold expanding window cross-validation
- **Forecast Horizon:** 14 days
- **Minimum Training Periods:** 56 days per fold

### Evaluation Metrics
- **MAE (Mean Absolute Error)** - Primary metric
- **RMSE (Root Mean Squared Error)** - Secondary metric
- **sMAPE (Symmetric Mean Absolute Percentage Error)**
- **Bias** - Systematic over/under-prediction
- **Coverage (80% Prediction Intervals)** - Target: 75-85%
- **R²** - Variance explained

### Feature Set (Exogenous Regressors)
- **Day-of-Week:** 6 one-hot features (Monday-Saturday, dow_0 to dow_5)
  - Sunday (dow_6) dropped to avoid collinearity
- **Calendar Features:**
  - `is_holiday` - Holiday flag
  - `pre_holiday` - Day before holiday
  - `post_holiday` - Day after holiday
  - Weekend flag (is_weekend) - may be dropped due to collinearity

### Baseline Comparisons
All models must beat these naive baselines:
- **Seasonal Naive (7-day lag):** MAE = 38.00, RMSE = 71.34
- **Moving Average (7-day):** MAE = 116.11, RMSE = 130.08

---

## Current Champion: AutoARIMA v2.1 🏆

### Model Configuration
```
Framework: Nixtla StatsForecast AutoARIMA
Seasonal: False (features handle seasonality)
Season Length: 1
Uses Exogenous: True (9 features)

Exogenous Features:
  - dow_0, dow_1, dow_2, dow_3, dow_4, dow_5 (Monday-Saturday one-hot)
  - is_holiday
  - pre_holiday
  - post_holiday

Calibration:
  - Day-of-week specific bias corrections (7 values)
  - Interval scaling factor: 1.067×
  - Coverage guard rails: 75-85% target range enforced
```

### Cross-Validated Performance (4-Fold Expanding Window)

**Raw Metrics (Pre-Calibration):**
```
MAE:     36.39
RMSE:    57.80
sMAPE:   46.97%
Bias:    +6.54
Coverage: 75.0%
```

**Calibrated Metrics (Production-Ready):**
```
MAE:     33.66  ✅ 11.4% better than seasonal naive
RMSE:    55.71  ✅ 21.9% better than seasonal naive
sMAPE:   39.67%
Bias:    ~0.00  ✅ Perfect calibration
Coverage: 76.8% ✅ Within target range (75-85%)
```

### Day-of-Week Performance Breakdown
```
Day         Bias      MAE     Note
─────────────────────────────────────────────────
Monday      +16.24    78.65   Highest variance
Tuesday     +19.94    27.48   
Wednesday   +3.57     29.43   
Thursday    -13.35    32.43   
Friday      -14.38    31.68   
Saturday    +13.14    24.95   Best performance
Sunday      +20.60    30.10   
```

### Improvements vs Baselines
```
vs Seasonal Naive:    +11.4% MAE improvement
vs Moving Average:    +71.0% MAE improvement
```

### Why It's Champion
✅ **Robust validation** - 4-fold CV provides reliable generalization estimates  
✅ **Perfect calibration** - DOW-specific bias corrections achieve ~0 bias  
✅ **Good intervals** - 76.8% coverage within 75-85% target  
✅ **Beats baselines** - Significantly better than naive methods  
✅ **Production-ready** - Full MLOps pipeline with artifacts, tests, guard rails  
✅ **Comprehensive training** - 154 days spanning seasonal transitions  

### Production Infrastructure
- Makefile automation: `make daily-forecast`
- Artifact versioning with timestamps
- Run manifests linking all outputs
- SQLite persistence for forecasts
- Calibration reports in `reports/forecast_quality.md`
- Unit test coverage and smoke tests
- Guard rails preventing bad deployments

### Artifacts Location
```
Model:     artifacts/models/champion_autoarima_20251025_064255.pkl
Backtest:  artifacts/metrics/daily_champion_backtest_20251025_064255.csv
Metrics:   artifacts/metrics/daily_champion_metrics_20251025_064255.json
Forecast:  artifacts/forecasts/daily_champion_forecast_raw_20251025_064255.csv
```

---

## Challenger: Greykite (Baseline_v2)

### Status
⚠️ **Testing Incomplete** - Single test set evaluation only (not CV)  
⚠️ **Library not installed** - Currently blocked in branch environment  
⚠️ **Less training data** - Only 70 days vs 154 for AutoARIMA  

### Model Configuration
```
Framework: LinkedIn Greykite Silverkite
Yearly Seasonality: Auto
Weekly Seasonality: Auto
Normalize Method: zero_to_one
Fit Algorithm: linear

Regressors (2):
  - reg_dow (numeric 0-6)
  - reg_is_weekend (binary)

Autoregression:
  - Lag orders: [1, 7, 14]
  
Uncertainty: 10 simulation runs
```

### Performance (Single Test Set - 70 Days Training)

**Test Metrics:**
```
MAE:     24.52  ⚠️ Single test set only, not CV
RMSE:    33.62
R²:      0.9256 (92.6% variance explained)
sMAPE:   9.0%
MAPE:    21.2%
CORR:    0.962
Coverage: 78.6%
```

**Train Metrics:**
```
MAE:     25.78
RMSE:    43.15
R²:      0.8795
Coverage: 91.1%
```

### Improvement vs Greykite Baseline
```
vs baseline (weekend only): +7.6% MAE improvement
```

### Why Not Champion (Yet)
❌ **Different validation** - Single test set vs 4-fold CV (not comparable)  
❌ **Less training data** - 70 days vs 154 days  
❌ **No baseline comparison** - Not tested against seasonal naive/MA  
❌ **No bias calibration** - No explicit DOW-specific corrections  
❌ **Infrastructure gaps** - No Makefile automation, limited tests  
❌ **Blocked features** - Patsy parser prevents rolling stat features  

### Key Findings
✅ **Native autoregression works** - Lags [1, 7, 14] capture dynamics  
✅ **Good single-test performance** - 24.52 MAE on specific test period  
✅ **Fast training** - Quick iterations  
✅ **Built-in uncertainty** - Simulation-based intervals  

### Known Issues
- **Patsy parser blocks rolling features** - Column names like `inbox_total_roll_7_mean` cause failures
- **No cross-validation run yet** - Need CV to compare fairly with AutoARIMA
- **Feature set mismatch** - Uses numeric DOW + weekend vs AutoARIMA's one-hot DOW + holidays

---

## Testing Requirements for Prophet (To Ensure Fair Comparison)

### Data Requirements
✅ **Use same training window:** 154 days (2025-05-18 to 2025-10-23)  
✅ **Use same validation method:** 4-fold expanding window cross-validation  
✅ **Use same forecast horizon:** 14 days  
✅ **Use same minimum training:** 56 days per fold  

### Feature Requirements
✅ **Use same exogenous regressors:**
  - Day-of-week features (dow_0 to dow_5 or Prophet's built-in)
  - Holiday features (is_holiday, pre_holiday, post_holiday)
  - Prophet can use built-in holiday handling

✅ **Test with Prophet's native seasonality:**
  - Weekly seasonality
  - Yearly seasonality (if applicable)
  - Holiday effects

### Evaluation Requirements
✅ **Compute same metrics:**
  - MAE, RMSE, sMAPE, Bias, Coverage (80% PI)
  - Day-of-week breakdown
  - Comparison vs seasonal naive and MA(7) baselines

✅ **Apply calibration:**
  - DOW-specific bias corrections (if needed)
  - Interval scaling to achieve 75-85% coverage
  - Document calibration factors

✅ **Generate artifacts:**
  - CV backtest results CSV
  - Metrics JSON with all metrics
  - Raw and calibrated forecasts
  - Model pickle file
  - Run manifest linking outputs

### Success Criteria
For Prophet to be considered as champion/challenger:
1. **Beat seasonal naive** - MAE < 38.00
2. **Beat moving average** - MAE < 116.11
3. **Competitive with AutoARIMA** - MAE within ±10% of 33.66
4. **Good coverage** - 75-85% for 80% prediction intervals
5. **Low bias** - DOW-adjusted bias near 0
6. **Complete artifacts** - Full audit trail

---

## Next Steps for Prophet Testing

### Phase 1: Setup
1. Install `prophet` library (Facebook Prophet / PyTorch)
2. Create `scripts/run_daily_prophet.py` similar to existing Greykite script
3. Create `src/models/prophet_runner.py` for Prophet configuration

### Phase 2: Feature Engineering
1. Map existing calendar features to Prophet format
2. Configure Prophet's built-in:
   - Weekly seasonality
   - Holiday effects (use is_holiday, pre_holiday, post_holiday)
3. Add custom regressors (DOW if needed beyond Prophet's built-in)

### Phase 3: Cross-Validation
1. Implement 4-fold expanding window CV
2. Use same folds as AutoARIMA for direct comparison
3. Compute metrics per fold and aggregate

### Phase 4: Calibration
1. Apply DOW-specific bias corrections
2. Scale intervals to achieve 75-85% coverage
3. Generate calibrated forecasts

### Phase 5: Comparison
1. Compare Prophet CV metrics vs AutoARIMA CV metrics
2. Compare Prophet vs Greykite (once Greykite CV is run)
3. Test against baselines (seasonal naive, MA7)
4. Generate comparison report: `reports/prophet_vs_champion.md`

### Phase 6: Production
1. Create Makefile target: `make run-daily-prophet`
2. Add to CI: `ci/run_forecast_checks.sh`
3. Implement guard rails
4. Create promotion criteria

---

## Greykite Testing TODO (For Fair Comparison)

### Before Comparing with Prophet
1. ✅ Install Greykite library
2. ✅ Train on full 154 days (match AutoARIMA)
3. ✅ Run 4-fold expanding window CV (match methodology)
4. ✅ Add naive baseline comparisons
5. ✅ Fix Patsy rolling feature issues (if needed)
6. ✅ Apply DOW-specific bias calibration
7. ✅ Generate full artifacts and metrics
8. ✅ Update this document with CV results

### Known Blockers for Greykite
- Patsy parser issue with rolling feature column names
- Need to resolve: Use Q() function, rename columns, or compute inside Greykite

---

## Champion Selection Criteria (For All Models)

### Performance Metrics (40%)
- Cross-validated MAE (primary)
- Cross-validated RMSE (secondary)
- sMAPE, Bias, Coverage

### Validation Rigor (30%)
- 4-fold expanding window CV (required)
- Multiple baseline comparisons
- DOW-specific analysis

### Production Readiness (20%)
- Makefile automation
- Artifact management
- Test coverage
- Guard rails

### Calibration Quality (10%)
- Near-zero bias after calibration
- Coverage within 75-85% target
- Stable across days of week

---

## Summary Table (Ready for Prophet Addition)

| Model | Framework | Training Days | Validation | MAE (CV) | RMSE (CV) | Bias | Coverage | vs Naive | Status |
|-------|-----------|---------------|------------|----------|-----------|------|----------|----------|--------|
| **AutoARIMA v2.1** | StatsForecast | 154 | 4-fold CV | **33.66** | **55.71** | **~0.00** | **76.8%** | **+11.4%** | ✅ **Champion** |
| Greykite baseline_v2 | Greykite | 70 | Single test | 24.52* | 33.62* | Unknown | 78.6% | Unknown | ⚠️ Incomplete |
| Prophet | Prophet | TBD | TBD | TBD | TBD | TBD | TBD | TBD | 🔄 Pending |

**Note:** Greykite numbers marked with * are single test set only, not CV. Not directly comparable to AutoARIMA.

---

## References

- AutoARIMA metrics: `artifacts/metrics/daily_champion_metrics_20251025_064255.json`
- Greykite comparison: `reports/model_comparison_greykite_vs_autoarima.md`
- Phase 1 results: `reports/phase1_results.md`
- Architecture: `docs/architecture.md`
- Decision log: `artifacts/metrics/decision_log.yaml`

---

**Document Owner:** Robostradamus Team  
**Version:** 1.0  
**Last Reviewed:** 2025-10-25
