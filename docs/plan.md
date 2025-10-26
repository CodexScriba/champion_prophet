## System Requirements – Prophet Initiative

### Execution Environment
- 64-bit Linux or macOS workstation/runner with at least 16 GB RAM (Stan compilation + CV folds).
- Python 3.10+ (align with champion stack) managed via `pyenv`, `uv`, or Conda.
- Local shell utilities: `make`, `git`, `curl`, `tar`, `gzip`.

### Python Tooling
- Virtual environment management (`uv`, `venv`, or Conda) with pip available.
- Core libraries: `prophet>=1.1`, `pandas>=2.1`, `numpy>=1.26`, `scikit-learn>=1.4`, `holidays`, `cmdstanpy`.
- Supporting stack reused from champion pipeline: `pyyaml`, `statsmodels`, `tqdm`, `joblib`, `matplotlib`, `plotly`.
- Testing / linting: `pytest`, `coverage`, `ruff` (match repo standards once confirmed).

### Build Toolchain
- Modern C++ compiler (g++ ≥ 9 or clang ≥ 11) and `make` for Stan/CmdStan builds.
- For macOS: Xcode Command Line Tools; for Linux: `build-essential`/`gcc`, `gfortran`.
- Sufficient disk (~5 GB) for CmdStan binaries, model artifacts, and CV outputs.

### Data & Storage
- Read/write access to `database/email_database.db` (SQLite) and JSON mirror.
- Permissions to create timestamped artifact directories under `artifacts/`.
- Optional: configure environment variable for database URI override (`EMAIL_DB_PATH` placeholder).

### Automation & Reporting
- Ability to extend Makefile (`make run-daily-prophet`) and CI scripts (`ci/run_forecast_checks.sh`).
- Markdown report generation tooling (existing Python templating or Jinja2).
- Logging/manifest storage (YAML/JSON) consistent with champion pipeline format.

### Optional Enhancements
- GPU not required; CPU parallelism via `cmdstanpy` threads (ensure OpenMP support).
- Containers: Dockerfile updates if reproducible build images are desired.

---

## Phase Plan – Path to Prophet Championship

### Phase 0 – Environment Bootstrap
- **Objective:** Establish a reproducible development environment ready for Prophet experimentation.
- **Key Tasks:** Install Python deps (`prophet`, `cmdstanpy`, supporting libs), configure C++ toolchain, pin versions in dependency files, smoke-test import of Prophet + CmdStan build.
- **Deliverables:** `requirements.txt`/`pyproject` updates, environment bootstrap docs, verified Prophet install log.

### Phase 1 – Daily Data Foundation
- **Objective:** Build reliable daily-level data access covering the full date range in the SQLite/JSON sources.
- **Key Tasks:** Implement shared data loader with schema validation, impute/flag missing values, align holiday calendar, persist intermediate daily dataset for reuse.
- **Deliverables:** `src/data/daily_loader.py`, validation report, unit tests on boundary dates and flag consistency.

### Phase 2 – Feature Engineering & Regressors (Daily)
- **Objective:** Produce Prophet-ready feature matrix mirroring champion regressors.
- **Key Tasks:** Encode DOW signals (allowing Prophet’s internal vs custom), integrate `is_holiday`, `pre/post_holiday`, handle changepoints & growth assumptions, document feature configs.
- **Deliverables:** Feature generation module, configuration YAML for toggles, exploratory notebook/plots verifying feature impacts.

### Phase 3 – Daily Prophet Modeling & CV
- **Objective:** Train Prophet models on the full 154-day window with champion-aligned 4-fold expanding CV.
- **Key Tasks:** Implement `scripts/run_daily_prophet.py`, reuse fold definitions, add hyperparameter sweep grid, log per-fold metrics, capture raw forecasts.
- **Deliverables:** Serialized Prophet models per fold, CV metrics tables, run manifest entries.

### Phase 4 – Calibration & Interval Tuning
- **Objective:** Match champion calibration quality with DOW bias corrections and interval scaling.
- **Key Tasks:** Derive residual diagnostics, compute DOW offsets, tune `interval_width`/scaling to hit 75–85% coverage, apply to holdout forecasts, visualize results.
- **Deliverables:** Calibration module, updated forecast artifacts (raw + calibrated), bias/coverage report.

### Phase 5 – Comparison & Promotion Criteria
- **Objective:** Benchmark Prophet daily results against baselines and AutoARIMA champion.
- **Key Tasks:** Run seasonal naive & MA7 baselines for same folds, compile comparison dashboards, verify success criteria (MAE thresholds, bias, coverage), document findings.
- **Deliverables:** `reports/prophet_vs_champion.md`, metrics JSON with comparison block, decision checklist.

### Phase 6 – Production Integration
- **Objective:** Integrate Prophet pipeline into existing automation and guard rails.
- **Key Tasks:** Extend Makefile (`make run-daily-prophet`), update CI scripts, add artifact retention policies, ensure logging + failure guard rails align with champion standards.
- **Deliverables:** Makefile/CI diffs, automated artifact manifest, smoke-test logs.

### Phase 7 – Hourly Expansion (Post-Daily Success)
- **Objective:** Extend pipeline to hourly forecasting after daily champion goals are met.
- **Key Tasks:** Build hourly dataset loader keyed on `has_sla_data`, engineer intraday regressors, adapt Prophet settings for sub-daily seasonality, run CV tailored to hourly horizon.
- **Deliverables:** Hourly data module, hourly Prophet runner prototype, evaluation report vs future hourly baselines.

### Phase 8 – Continuous Improvement Loop
- **Objective:** Institutionalize monitoring, retraining cadence, and experimentation.
- **Key Tasks:** Schedule periodic retrains, implement drift/alerting dashboard, backlog enhancement ideas (e.g., holiday priors, external regressors, hierarchical combos).
- **Deliverables:** Monitoring plan, backlog tracker, documented retrain SOP.
