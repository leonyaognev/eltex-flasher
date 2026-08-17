import os
from pathlib import Path

URL = "https://validator-v2.eltex.loc"
DOWNLOAD_DIR = Path.home() / "work_pc"

VALIDATOR_USER = os.environ["VALIDATOR_USER"]
VALIDATOR_PASSWORD = os.environ["VALIDATOR_PASSWORD"]

variables = {
    "tftp_link": "",
}
