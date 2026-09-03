from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import os


def _env(key: str, default: str | None = None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise RuntimeError(f"Environment variable {key} is not set")
    return value


def _env_int(key: str, default: int) -> int:
    return int(_env(key, str(default)))


def _env_bool(key: str, default: bool) -> bool:
    return _env(key, str(default)).lower() in ("1", "true", "yes")


def _env_path(key: str, default: str | None = None) -> Path:
    return Path(_env(key, default)).expanduser()


# Validator (Web UI)
VALIDATOR_URL = _env("VALIDATOR_URL", "https://validator-v2.eltex.loc")
VALIDATOR_USER = _env("VALIDATOR_USER")
VALIDATOR_PASSWORD = _env("VALIDATOR_PASSWORD")

# SSH (Ansible)
SWITCH_USERNAME = _env("SWITCH_USERNAME", "admin")
ANSIBLE_PASSWORD = _env("ANSIBLE_PASSWORD", "admin")
TFTP_SERVER_IP = _env("TFTP_SERVER_IP", "192.168.246.95")

# Paths
DOWNLOAD_DIR = _env_path("DOWNLOAD_DIR", "~/work_pc")
ANSIBLE_INVENTORY = _env("ANSIBLE_INVENTORY", "inventory.yml")
ANSIBLE_PLAYBOOK = _env("ANSIBLE_PLAYBOOK", "upgrade.yml")

# Timeouts & Delays (seconds)
RETRY_DELAY = _env_int("RETRY_DELAY", 2)
POLL_INTERVAL = _env_int("POLL_INTERVAL", 30)
POLL_GRANULARITY = _env_int("POLL_GRANULARITY", 1)
POST_UPGRADE_DELAY = _env_int("POST_UPGRADE_DELAY", 2)
ANSIBLE_COMMAND_TIMEOUT = _env_int("ANSIBLE_COMMAND_TIMEOUT", 600)

# Download
DOWNLOAD_CHUNK_SIZE = _env_int("DOWNLOAD_CHUNK_SIZE", 8192)

# SSL
VERIFY_SSL = _env_bool("VERIFY_SSL", False)

# Image
IMAGE_TO_SWITCH: dict[str, list] = {
    # ph4:
    "curr_image_msys": ["192.168.246.93"],
    # ph5:
    "curr_image_ac5": [
        # "192.168.246.92",
        "192.168.246.94",
    ],
}
