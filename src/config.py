from pathlib import Path

from dotenv import load_dotenv

import json
import os

load_dotenv()
with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)


def _env(key: str, default: str | None = None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise RuntimeError(f"Environment variable {key} is not set")
    return value


# Validator (Web UI)
VALIDATOR_URL = config["validator"]["url"]
VALIDATOR_USER: str = _env("VALIDATOR_USER")
VALIDATOR_PASSWORD: str = _env("VALIDATOR_PASSWORD")

# SSH (Ansible)
SWITCH_USERNAME: str = _env("SWITCH_USERNAME", "admin")
ANSIBLE_PASSWORD: str = _env("ANSIBLE_PASSWORD", "admin")
TFTP_SERVER_IP: str = config["ssh"]["tftp_server_ip"]

# Paths
DOWNLOAD_DIR: str = config["paths"]["download_dir"]
ANSIBLE_INVENTORY: str = config["paths"]["ansible_inventory"]
ANSIBLE_PLAYBOOK: str = config["paths"]["ansible_playbook"]

# Timeouts & Delays (seconds)
RETRY_DELAY: int = int(config["timeouts"]["retry_delay"])
POLL_INTERVAL: int = int(config["timeouts"]["poll_interval"])
POLL_GRANULARITY: int = int(config["timeouts"]["poll_granularity"])
POST_UPGRADE_DELAY: int = int(config["timeouts"]["post_upgrade_delay"])
ANSIBLE_COMMAND_TIMEOUT: int = int(config["timeouts"]["ansible_command_timeout"])

# Download
DOWNLOAD_CHUNK_SIZE: int = config["download"]["chunk_size"]

# Images
IMAGE_TO_SWITCH: dict[str, list[str]] = config["images"]
