# AWS-env

A desktop GUI for AWS MFA authentication. Enter your 6-digit MFA token, get 12-hour session credentials written to `~/.aws/credentials`, and optionally log into Docker/ECR — all in one click.

## Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **AWS CLI configured** — run `aws configure` with your Access Key ID and Secret Access Key. This creates `~/.aws/credentials` with a `[default]` profile.
- **MFA serial ARN** — add `mfa_serial = arn:aws:iam::ACCOUNT:mfa/USERNAME` to `~/.aws/config` under `[default]`:

  ```ini
  [default]
  region = eu-west-1
  mfa_serial = arn:aws:iam::123456789012:mfa/your.name
  ```

  Alternatively, set the `AWS_MFA_ARN` environment variable.

## Setup

```bash
git clone <repo-url>
cd aws-env-py

python -m venv .venv

# Windows
.venv\Scripts\pip install -r requirements.txt

# Linux / macOS
.venv/bin/pip install -r requirements.txt
```

## Usage

```bash
# Windows
.venv\Scripts\python main.py

# Linux / macOS
.venv/bin/python main.py
```

1. Enter your 6-digit MFA token
2. Click **Login** (or enable **Auto Enter** to submit automatically when 6 digits are typed)
3. Session credentials are written to `~/.aws/credentials` under the configured profile (default: `wint`)

### Options

| Checkbox | Effect |
|---|---|
| **New Creds** | Generate fresh session credentials via STS (requires MFA token). Uncheck to use existing credentials. |
| **Docker** | Log into the ECR Docker registry after authentication |
| **Helm** | Helm registry login (placeholder) |
| **Auto Enter** | Automatically click Login when 6 digits are entered |
| **Audio** | Play a sound on success/failure |
| **Debug** | Show debug-level log messages |

### Configuration

Click **Save Config** to persist your settings (region, profile, registry, checkboxes) to `~/.wde/wde_config.yaml`. They'll be restored automatically on next launch.

## System Tray

A tray icon appears in your taskbar. Left-click to show/hide the window. Closing the window fully exits the app.

## Troubleshooting

- **"MFA serial not found"** — Make sure `mfa_serial` is set in `~/.aws/config` under `[default]`, or set the `AWS_MFA_ARN` environment variable.
- **"AccessDenied ... invalid MFA one time pass code"** — The MFA token was wrong or expired. Tokens are time-based and valid for ~30 seconds.
- **"No credentials found for profile"** — Run with **New Creds** checked first to generate session credentials.
- **Docker login fails** — Make sure Docker Desktop is running and the `docker` CLI is on your PATH.
