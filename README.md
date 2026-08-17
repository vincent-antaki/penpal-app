# App

Streamlit-based web gallery for Penpal.

## Overview

This application serves as a gallery and control center for generated plot outputs. It visualizes SVGs alongside their metadata, parameter configurations, and Git commit hashes.

## Modes

- **Regular Outputs**: Browse production runs generated through the CLI runner.
- **Test Outputs**: Browse development runs and use the UI to experiment with JSON parameters. Can also edit the parameters and launch a run; this allows for quick tweaking and exploration of a project.

## Usage

You can launch the dashboard using the default paths, or optionally override them with CLI arguments or environment variables.

```bash
uv run python -m streamlit run main.py
```

### Configuration Cascade

The app uses the following hierarchy to resolve directories (highest priority first):
1. **CLI Arguments** (`--gallery-dir`, `--project-dir`, `--runner-script-path`)
2. **Environment Variables** (`PENPAL_GALLERY_DIR`, `PENPAL_PROJECT_DIR`, `PENPAL_RUNNER_SCRIPT_PATH`)
3. **Defaults** (Relative to the workspace, e.g. `../gallery`, `../projects`)

- `--gallery-dir` / `PENPAL_GALLERY_DIR`: Path to the gallery directory where outputs will be written/read from.
- `--project-dir` / `PENPAL_PROJECT_DIR`: Path to the projects directory.
- `--runner-script-path` / `PENPAL_RUNNER_SCRIPT_PATH`: Path to the Python runner script (e.g. `tools/runner.py`).
