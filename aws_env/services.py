import base64
import logging
import subprocess
from dataclasses import dataclass

import boto3

log = logging.getLogger(__name__)


@dataclass
class BasicCreds:
    username: str
    password: str


def ecr_login(session_creds: dict, region: str) -> list[BasicCreds]:
    """Get ECR authorization tokens and decode to username/password."""
    try:
        session = boto3.Session(
            aws_access_key_id=session_creds["aws_access_key_id"],
            aws_secret_access_key=session_creds["aws_secret_access_key"],
            aws_session_token=session_creds.get("aws_session_token"),
            region_name=region,
        )
        ecr = session.client("ecr")
        response = ecr.get_authorization_token()
        result = []
        for auth in response["authorizationData"]:
            decoded = base64.b64decode(auth["authorizationToken"]).decode()
            username, password = decoded.split(":", 1)
            result.append(BasicCreds(username=username, password=password))
            log.info("ECR authorization token retrieved for %s", username)
        return result
    except Exception as e:
        log.error("ECR login failed: %s", e)
        return []


def docker_login(creds: BasicCreds, registry: str) -> bool:
    """Log into Docker registry via CLI (password piped to stdin)."""
    try:
        proc = subprocess.run(
            ["docker", "login", "--username", creds.username, "--password-stdin", registry],
            input=creds.password,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0 and "Login Succeeded" in proc.stdout:
            log.info("Docker login succeeded for %s", registry)
            return True
        log.error("Docker login failed: %s", proc.stderr or proc.stdout)
        return False
    except FileNotFoundError:
        log.error("Docker CLI not found")
        return False
    except Exception as e:
        log.error("Docker login failed: %s", e)
        return False


def helm_login(creds: BasicCreds, registry: str) -> bool:
    """Helm registry login (placeholder — mirrors Java stub)."""
    log.info("Helm login not yet implemented")
    return True
