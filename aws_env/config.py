from dataclasses import dataclass, asdict, fields
from pathlib import Path

import yaml

CONFIG_DIR = Path.home() / ".wde"
CONFIG_FILE = CONFIG_DIR / "wde_config.yaml"


@dataclass
class AppConfig:
    aws_region: str = "eu-west-1"
    aws_profile: str = "wint"
    ecr_registry: str = "742958722076.dkr.ecr.eu-west-1.amazonaws.com"
    new_creds_enabled: bool = True
    debug_enabled: bool = False
    docker_enabled: bool = False
    helm_enabled: bool = False
    audio_enabled: bool = True
    auto_enter: bool = True


def save_config(config: AppConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(asdict(config), f, default_flow_style=False)


def load_config() -> AppConfig:
    if not CONFIG_FILE.exists():
        return AppConfig()
    with open(CONFIG_FILE) as f:
        data = yaml.safe_load(f) or {}
    known = {field.name for field in fields(AppConfig)}
    return AppConfig(**{k: v for k, v in data.items() if k in known})
