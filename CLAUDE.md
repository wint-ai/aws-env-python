# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AWS-env is a Python/tkinter desktop GUI that simplifies AWS MFA authentication. It generates temporary session credentials via AWS STS, writes them to `~/.aws/credentials`, and optionally authenticates Docker with ECR. Built for WINT Ltd, defaults to the `wint` AWS profile in `eu-west-1`.

## Build & Run

```bash
# Create venv and install deps (first time only)
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# .venv/bin/pip install -r requirements.txt     # Linux/macOS

# Run
.venv/Scripts/python -m aws_env   # Windows
# .venv/bin/python -m aws_env     # Linux/macOS
```

No build step — just run `python -m aws_env` directly. On Windows, double-click `run.vbs` to launch without a console window.

## Tech Stack

- **Python 3.10+** (uses `list[]` type hints)
- **tkinter** — GUI (stdlib, no install needed)
- **boto3** — AWS SDK (STS, ECR)
- **pyyaml** — App config persistence
- **pystray + Pillow** — System tray icon (optional, app works without them)

## Architecture

All source lives in the `aws_env/` package. Five modules, no framework, no abstraction layers:

```
aws_env/
    __init__.py      → Package marker
    __main__.py      → `python -m aws_env` entry point
    main.py          → tkinter root, system tray setup
    gui.py           → MainWindow class (all UI + login orchestration)
    config.py        → AppConfig dataclass + YAML persistence (~/.wde/wde_config.yaml)
    credentials.py   → Read/write ~/.aws/credentials, STS GetSessionToken, validation
    services.py      → ECR auth token decoding, Docker CLI login, Helm stub
```

### Credential Flow

1. Base IAM credentials (access key + secret, no session token) live in `~/.aws/credentials` under `[default]`
2. MFA serial ARN is read from `~/.aws/config` `[default]` section (`mfa_serial` key), fallback to `AWS_MFA_ARN` env var
3. `credentials.generate_session_credentials()` calls STS `GetSessionToken` with MFA serial + token code, 24-hour duration
4. `credentials.write_credentials()` writes the resulting session creds (key + secret + session token) to `~/.aws/credentials` under the configured profile (default: `[wint]`)
5. `services.ecr_login()` uses the session creds to get ECR auth tokens, decodes base64 `username:password`
6. `services.docker_login()` pipes the password to `docker login --password-stdin`

### GUI (gui.py)

`MainWindow` is the only UI class. It owns:
- All tkinter widgets (region combo, profile field, MFA input, checkboxes, log area)
- Login orchestration (`_exec_login` runs in a background thread)
- Config ↔ UI binding (`_load_config_to_ui`, `_ui_to_config`)
- A `TextHandler` logging handler that routes Python `logging` output to the ScrolledText widget
- MFA input validation (6 digits only, auto-enter when complete)
- Credential expiry reminder via `threading.Timer` (fires 30 min before 24-hour session ends)

### Config (config.py)

`AppConfig` is a plain dataclass with defaults matching the Java version. Serialized to `~/.wde/wde_config.yaml` via PyYAML. Unknown fields in the YAML are silently ignored (forward compatibility).

### System Tray (main.py)

Optional — if pystray/Pillow are installed, a green circle icon appears in the system tray. Left-click (default action) toggles window visibility. Right-click menu has Show/Hide and Exit. Closing the window via X fully exits the app and cleans up the tray icon.

## Key Constants

Defaults are in `aws_env/config.py:AppConfig`:
- `aws_profile = "wint"`
- `aws_region = "eu-west-1"`
- `ecr_registry = "742958722076.dkr.ecr.eu-west-1.amazonaws.com"`

Session duration is in `aws_env/credentials.py`:
- `SESSION_DURATION = 86400` (24 hours)

## Porting Notes

This is a Python rewrite of the Java/JavaFX version in the parent directory. The Java version uses JPMS modules, Gradle with jlink/jpackage, and Apache Commons Configuration2 for INI parsing. The Python version replaces all of that with stdlib `configparser`, `boto3`, and `tkinter`. The `HelmService` is a stub in both versions.
