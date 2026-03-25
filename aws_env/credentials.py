import configparser
import logging
import os
from pathlib import Path
from typing import Optional

import boto3
import botocore.exceptions

log = logging.getLogger(__name__)

AWS_DIR = Path.home() / ".aws"
CREDENTIALS_FILE = AWS_DIR / "credentials"
CONFIG_FILE = AWS_DIR / "config"
SESSION_DURATION = 86400  # 24 hours


def get_mfa_serial() -> Optional[str]:
    """Get MFA device ARN from ~/.aws/config [default] or AWS_MFA_ARN env var."""
    if CONFIG_FILE.exists():
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        for section in ["default", "profile default"]:
            if config.has_section(section) and config.has_option(section, "mfa_serial"):
                return config.get(section, "mfa_serial")
    return os.environ.get("AWS_MFA_ARN")


def read_credentials(profile: str) -> Optional[dict]:
    """Read existing credentials from the given profile in ~/.aws/credentials."""
    if not CREDENTIALS_FILE.exists():
        return None
    config = configparser.ConfigParser()
    config.read(CREDENTIALS_FILE)
    if not config.has_section(profile):
        return None
    try:
        return {
            "aws_access_key_id": config.get(profile, "aws_access_key_id"),
            "aws_secret_access_key": config.get(profile, "aws_secret_access_key"),
            "aws_session_token": config.get(profile, "aws_session_token", fallback=None),
        }
    except configparser.NoOptionError:
        return None


def generate_session_credentials(region: str, token_code: str) -> Optional[dict]:
    """Call STS GetSessionToken with MFA and return temporary credentials."""
    mfa_serial = get_mfa_serial()
    if not mfa_serial:
        log.error("MFA serial not found in ~/.aws/config or AWS_MFA_ARN env var")
        return None
    try:
        sts = boto3.client("sts", region_name=region)
        response = sts.get_session_token(
            DurationSeconds=SESSION_DURATION,
            SerialNumber=mfa_serial,
            TokenCode=token_code,
        )
        creds = response["Credentials"]
        expiration = creds["Expiration"]
        log.info(
            "Session credentials generated, expire at %s",
            expiration.strftime("%H:%M:%S - %Y-%m-%d"),
        )
        return {
            "aws_access_key_id": creds["AccessKeyId"],
            "aws_secret_access_key": creds["SecretAccessKey"],
            "aws_session_token": creds["SessionToken"],
            "expiration": expiration,
        }
    except botocore.exceptions.ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_msg = e.response["Error"]["Message"]
        log.error("AWS error (%s): %s", error_code, error_msg)
        return None
    except Exception as e:
        log.error("Failed to generate session credentials: %s", e)
        if log.isEnabledFor(logging.DEBUG):
            log.debug("Stack trace:", exc_info=True)
        return None


def write_credentials(profile: str, creds: dict) -> None:
    """Write session credentials to ~/.aws/credentials under the given profile.

    WARNING: configparser rewrites the entire file, stripping comments and
    potentially reordering sections.
    """
    config = configparser.ConfigParser()
    if CREDENTIALS_FILE.exists():
        config.read(CREDENTIALS_FILE)
    if not config.has_section(profile):
        config.add_section(profile)
    config.set(profile, "aws_access_key_id", creds["aws_access_key_id"])
    config.set(profile, "aws_secret_access_key", creds["aws_secret_access_key"])
    if creds.get("aws_session_token"):
        config.set(profile, "aws_session_token", creds["aws_session_token"])
    with open(CREDENTIALS_FILE, "w") as f:
        config.write(f)


def update_credentials(profile: str, region: str, token_code: str) -> Optional[dict]:
    """Generate new session credentials and write them to the credentials file."""
    creds = generate_session_credentials(region, token_code)
    if not creds:
        return None
    write_credentials(profile, creds)
    return creds


def validate_credentials(profile: str, region: str) -> bool:
    """Check if existing credentials are still valid via GetCallerIdentity."""
    creds = read_credentials(profile)
    if not creds or not creds.get("aws_session_token"):
        return False
    try:
        session = boto3.Session(
            aws_access_key_id=creds["aws_access_key_id"],
            aws_secret_access_key=creds["aws_secret_access_key"],
            aws_session_token=creds["aws_session_token"],
            region_name=region,
        )
        sts = session.client("sts")
        response = sts.get_caller_identity()
        return bool(response.get("UserId"))
    except Exception:
        return False
