# Contributing

## Local setup

1. Create a virtual environment.
2. Install runtime and dev dependencies.
3. Run the CLI from the repo root.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
python msm.py
```

## Project layout

- `core/`: runtime lifecycle, config loading, and per-server orchestration
- `db/`: SQLite persistence with WAL enabled
- `ui/`: interactive CLI flows and terminal presentation
- `utils/`: HTTP, RCON, archive, logging, and system helpers
- `tests/`: regression tests for parsing and security-sensitive helpers

## Verification

Run these before opening a pull request:

```bash
python -m flake8 --jobs=1 .
python -m black --check .
python -m pytest
python -m compileall msm.py core db ui utils tests
```

## Implementation notes

- Keep runtime state inside `ServerInstance`; do not reintroduce global process/session state.
- Preserve the ability to manage multiple running servers concurrently.
- Any backup restore logic must remain zip-slip safe.
- New config fields should be added through `ConfigManager` defaults so existing installs migrate cleanly.
