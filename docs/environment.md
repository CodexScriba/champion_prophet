# Prophet Environment Setup

This repository uses a PEP 621 `pyproject.toml` to manage Python
dependencies. The pinned versions in Phase 0 target a stable runtime for
Prophet experimentation while keeping compatibility with the existing
AutoARIMA stack.

## Requirements

- Python 3.10 or 3.11 (3.12 is currently unsupported by Prophet)
- C++14 toolchain for Stan/CmdStan builds (`gcc`/`clang` + `make`)
- 4 GB free disk space for the CmdStan toolchain cache

Install the base runtime using your preferred environment manager
(e.g. `uv`, `pyenv + venv`, or `conda`). The commands below assume a
standard virtual environment is active.

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

The editable install exposes future `src/` modules during development
and ensures notebooks/scripts share dependency versions.

## Prophet & CmdStan

The `prophet` wheel relies on `cmdstanpy` to compile Stan models on
first use. When running on a fresh machine or CI node, prime the cache
once to avoid runtime delays:

```python
python - <<'PY'
import cmdstanpy

cmdstanpy.install_cmdstan()
PY
```

- Use `CMDSTANPY_CACHE_DIR` to point installs at a writable cache
  directory (default: `~/.cmdstanpy`).
- Set `PROPHET_REPACKAGE_CMDSTAN=False` before installation if the host
  already provides a shared CmdStan build.

Common build issues:

- **Missing compiler toolchain** – install `build-essential` (Debian) or
  `xcode-select --install` (macOS).
- **Old `gcc` (<7)** – Stan requires full C++14 support.
- **CI timeouts** – pre-build CmdStan and cache the directory between
  runs.

## Optional Utilities

The `dev` extra adds formatting and notebook kernels used by the
experimentation workflow:

```bash
python -m pip install -e ".[dev]"
```

## Verification

Run a quick import check after installation:

```python
python - <<'PY'
import prophet
import cmdstanpy

print("Prophet", prophet.__version__)
print("CmdStanPy", cmdstanpy.__version__)
PY
```

Successful imports confirm that the Stan toolchain and Python bindings
are in place for Phase 1 modeling work.
