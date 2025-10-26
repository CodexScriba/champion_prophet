# Prophet Champion Delivery Plan

**Purpose:** Provide a focused, phase-based roadmap for delivering a Prophet-based forecasting system that can legitimately challenge the current AutoARIMA champion for email volume forecasting.

**Last Reviewed:** 2025-10-26

---

## Scope & Success Definition
- Deliver a daily Prophet model (MVP) that matches the AutoARIMA deployment contract on data handling, metrics, and monitoring.
- Extend to an hourly view only after the daily model meets promotion criteria.
- Produce production-ready assets (code, automation, documentation) so the model can be evaluated and promoted with minimal rework.

### Success Metrics
| Metric | Champion Target | Notes |
| --- | --- | --- |
| Daily MAE | ≤ 33.66 | Must be validated via the shared CV protocol.
| Daily Bias | \|bias\| ≤ 1.0 | Residual bias after calibration.
| Coverage | 75–85% | Based on calibrated 80% intervals.
| Guard rails | Pass | Alerting, documentation, backtest parity.

### Guardrails / Non-Negotiables
- Prophet evaluation must reuse the same data filters, cross-validation windows, and baselines used for AutoARIMA.
- All experimentation must be reproducible from tracked code + configuration (no notebook-only logic).
- Keep infrastructure simple: leverage existing tooling (uv/poetry, Make, CI) instead of inventing new orchestration unless justified.

---

## Delivery Principles
- **Champion parity first:** Every phase should answer “does this match or beat the current champion on the agreed scorecard?” before expanding scope.
- **Observable progress:** Prefer vertical slices that produce runnable scripts/notebooks with saved artifacts over exhaustive boilerplate upfront.
- **Tight feedback loops:** Instrument every phase with quick diagnostics—plots, fold metrics, residual analysis—to avoid blind spots discovered late.
- **Debt-aware:** Treat calibration, guard rails, and documentation as peer tasks, not afterthoughts.

---

## Phase 0 – Foundations
**Goal:** Establish a sane development environment, verify data pipelines, and set baselines for comparison.

**Key Activities**
- Add Prophet dependencies to the managed environment (`prophet>=1.1.5`, `cmdstanpy`, `pystan` if needed, `pandas`, `numpy`, `matplotlib`, `plotly`, `scikit-learn`). Pin versions and document installation quirks (cmdstan cache, compiler requirements).
- Run a data QA notebook/script that loads `database/email_database.db`, reports min/max dates, row counts, missing values, duplicate days, and schema parity. Parameterize start/end dates instead of hard-coding.
- Review existing champion artifacts (`artifacts/metrics`, `champion.md`) to capture baseline numbers and evaluation workflow.
- Define or update repository structure only where necessary. Reuse current patterns; avoid speculative directories.
- Stand up logging/config scaffolding shared by future scripts (structured logging, env-configured paths, deterministic random seeds).

**Deliverables**
- Environment guide or `pyproject.toml/requirements.txt` changes committed.
- Data QA report (markdown or notebook) stored under `docs/analysis/` or `notebooks/`.
- Shared configuration module (`src/config.py` or similar) with DB paths, default horizons, logging setup.
- Updated plan (this document) reviewed with stakeholders.

**Exit Criteria**
- `prophet` imports cleanly on the target runtime.
- Automated data QA passes without manual fixes or documents corrective actions.
- Champion baseline metrics captured in a shared location (`docs/baselines.md`).

---

## Phase 1 – Baseline Daily Model
**Goal:** Produce a minimal Prophet daily model that mirrors AutoARIMA’s data preparation and yields a single hold-out evaluation.

**Key Activities**
- Build a reusable loader that returns Prophet-ready frames (`ds`, `y`, optional regressors) with configurable date ranges and feature toggles (holidays, DOW indicators).
- Implement an initial `ProphetDailyModel` wrapper covering model instantiation, fit, forecast, and artifact persistence.
- Run a deterministic train/test split aligned with the champion reference horizon (e.g., last 14 days) and log MAE, RMSE, bias, coverage.
- Generate exploratory plots: forecast vs actuals, components, residual histograms. Store under `artifacts/plots/`.
- Compare against seasonal naive and champion metrics to establish a baseline gap analysis.

**Deliverables**
- `src/data/daily_loader.py` (or equivalent) with unit coverage for schema and date handling.
- `scripts/run_prophet_daily.py` or `notebooks/01_baseline_prophet.ipynb` producing an auditable forecast artifact.
- Baseline evaluation summary added to `docs/prophet_daily_baseline.md` including metric tables and observations.

**Exit Criteria**
- Script/notebook runs end-to-end without manual edits.
- Metrics and plots checked into version control.
- Baseline gap documented (areas where Prophet underperforms champion).

---

## Phase 2 – Daily Model Iteration & Cross-Validation
**Goal:** Achieve apples-to-apples comparison with AutoARIMA using expanding-window CV and targeted tuning.

**Key Activities**
- Reproduce the existing AutoARIMA fold logic via configuration (cutoffs, horizon, minimum train size). Prefer Prophet’s `cross_validation` API when possible; implement custom folds only if parity requires it.
- Introduce a small, justified hyperparameter grid (e.g., `changepoint_prior_scale`, `seasonality_prior_scale`, `seasonality_mode`) and evaluate via CV. Reference Prophet diagnostics guidelines for parameter ranges.
- Track per-fold and aggregate metrics, including day-of-week breakdowns, coverage, and bias.
- Summarize findings in a structured report highlighting best configuration, spread of errors, and comparison to champion.

**Deliverables**
- `src/models/prophet_daily.py` enhanced with CV helpers, or a dedicated `src/evaluation/prophet_cv.py` module.
- `scripts/run_prophet_cv.py` producing metrics JSON and fold forecasts under `artifacts/`.
- CV analysis report (`docs/prophet_daily_cv.md`) with tables/plots and recommendations for promotion readiness.

**Exit Criteria**
- Successful CV run stored and reproducible from CLI.
- Best configuration documented with rationale.
- Daily MAE within 10% of champion and clear plan for closing remaining gap.

---

## Phase 3 – Calibration, Diagnostics, and Champion Readiness
**Goal:** Close remaining metric gaps (bias, coverage) and prepare guard rails/documentation for a promotion decision.

**Key Activities**
- Analyze residuals for DOW/systematic bias. Implement calibration layers (additive adjustments, interval scaling, or Prophet’s `mcmc_samples`) supported by diagnostics.
- Validate calibrated model via out-of-time tests and ensure improvements generalize across folds.
- Ensure coverage target (75–85%) is met without sacrificing MAE.
- Build guard rail checks: metric regression tests, data drift detectors, failure alerts.
- Complete champion promotion packet: model card, assumptions, limitations, handoff checklist.

**Deliverables**
- Calibration utilities (`src/evaluation/calibration.py`) with tests.
- Updated evaluation scripts generating pre/post calibration comparisons.
- Champion readiness dossier (`docs/prophet_champion_packet.md`) including results, residual analyses, guard rail summary.

**Exit Criteria**
- Metrics meet or exceed promotion thresholds on CV and hold-out.
- Guard rail suite executes in CI or local automation with pass/fail signal.
- Stakeholders sign off on readiness to promote.

---

## Phase 4 – Production Integration
**Goal:** Integrate the Prophet solution into the production workflow with automation, monitoring, and documentation.

**Key Activities**
- Implement scheduled training/inference scripts or DAG tasks mirroring AutoARIMA’s deployment cadence.
- Persist model artifacts, forecasts, and diagnostics to agreed storage locations with retention policies.
- Wire up logging/metrics to existing observability stack (e.g., structured logs, Prometheus/Grafana, etc.).
- Update runbooks, operational docs, and troubleshooting guides for on-call parity.
- Conduct shadow or A/B runs to validate stability before champion swap.

**Deliverables**
- Production-ready runner (`scripts/prophet_daily_job.py` or orchestrated task definition) with configuration via environment or YAML.
- Monitoring checklist + dashboards/alerts configured.
- Operations docs appended to `docs/operations/`.

**Exit Criteria**
- Automated runs succeed across multiple cycles with clean logs.
- Monitoring/alerts validated via dry-run or chaos exercise.
- Promotion review completed (swap champion or document reasons to defer).

---

## Phase 5 – Hourly Extension (Conditional)
**Prerequisite:** Daily model meets champion criteria and production guard rails.

**Goal:** Deliver hourly forecasts that are consistent with daily totals and actionable for intraday planning.

**Key Activities**
- Audit availability and quality of hourly data (gaps, timezone alignment, business hours coverage).
- Decide between single multi-seasonal Prophet model, separate per-hour models, or top-down reconciliation.
- Prototype hourly forecasting, ensuring daily aggregates align with daily Prophet (≤5% deviation).
- Extend evaluation to include hour-level MAE, bias, and coverage metrics.
- Update automation/monitoring to handle higher frequency outputs.

**Deliverables**
- Hourly data loader and feature engineering utilities.
- Hourly evaluation report with reconciliation to daily totals.
- Updated production pipeline (if promoted).

**Exit Criteria**
- Hourly MAE < 10 and bias < 1 per hour on validation set.
- Daily aggregation of hourly forecasts stays within ±5% of the daily model.
- Stakeholder approval for rollout (if pursued).

---

## Engineering Backlog Snapshot
| Item | Status | Owner |
| --- | --- | --- |
| Dependency setup & doc | Not Started | T.B.D. |
| Data QA + baseline capture | Not Started | T.B.D. |
| Baseline daily runner | Not Started | T.B.D. |
| CV + tuning pipeline | Not Started | T.B.D. |
| Calibration toolkit | Not Started | T.B.D. |
| Production automation | Not Started | T.B.D. |
| Hourly feasibility study | Blocked (await Phase 3 exit) | T.B.D. |

---

## Risks & Mitigations
1. **Prophet underperforms champion:** Iterate on seasonality mode, changepoint priors, and regressors; consider hybrid residual models before abandoning.
2. **Limited history (≈5 months):** Prioritize weekly seasonality, use regularization, and validate robustness via bootstrapped folds.
3. **Holiday feature quality:** Validate holiday labels early; fall back to `add_country_holidays` or curated calendar if auto labels are noisy.
4. **Calibration drift in production:** Schedule periodic recalibration checks; alert when coverage/bias metrics move out of band.
5. **CmdStan runtime issues in CI:** Cache CmdStan build, document compiler requirements, and add health check script to CI.

---

## Open Questions / Decisions
- Do we standardize on `uv`, `poetry`, or another tool for dependency management across champions?
- Are there upcoming business events requiring custom holiday handling (e.g., promotions) that should be encoded as regressors?
- Should hourly forecasts feed directly into existing downstream systems or remain an analyst tool initially?
- What is the accepted champion promotion process (review board, sign-off cadence)?

---

## References
- `docs/architecture.md` – existing system context.
- `champion.md` – champion framework and decision rubric.
- `artifacts/metrics/` – current AutoARIMA performance snapshots.
- Prophet Diagnostics Guide (Facebook Prophet docs) for CV & tuning best practices.
