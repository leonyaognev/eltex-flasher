import re
from pathlib import Path
from typing import DefaultDict, Optional

import requests
import urllib3
from bs4 import BeautifulSoup

from .config import (
    DOWNLOAD_CHUNK_SIZE,
    DOWNLOAD_DIR,
    VALIDATOR_PASSWORD,
    VALIDATOR_URL,
    VALIDATOR_USER,
)

session = requests.Session()

session.verify = False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_csrf_from_login() -> str:
    response = session.get(f"{VALIDATOR_URL}/login/")
    response.raise_for_status()

    match = re.search(
        r'name="csrf_token"\s+value="([^"]+)"',
        response.text,
    )

    if not match:
        raise RuntimeError("CSRF token not found")

    return match.group(1)


def login() -> None:
    csrf_token = get_csrf_from_login()

    response = session.post(
        f"{VALIDATOR_URL}/login/",
        data={
            "login": VALIDATOR_USER,
            "password": VALIDATOR_PASSWORD,
            "csrf_token": csrf_token,
        },
    )
    response.raise_for_status()


def get_upload_csrf() -> str:
    response = session.get(f"{VALIDATOR_URL}/files/")
    response.raise_for_status()

    match = re.search(
        r'<meta\s+name="csrf-token"\s+content="([^"]+)"',
        response.text,
    )

    if not match:
        raise RuntimeError("Upload CSRF token not found")

    return match.group(1)


def get_latest_file() -> str:
    response = session.get(f"{VALIDATOR_URL}/files/")
    response.raise_for_status()

    return response.text


def parse_latest_file(html: str) -> tuple[Optional[str], Optional[str]]:
    soup = BeautifulSoup(html, "html.parser")

    last_id: Optional[str] = None

    for td in soup.find_all("td"):
        text = td.get_text(strip=True)

        if text.isdigit():
            last_id = text
            break

    element = soup.find(lambda tag: tag.has_attr("data-file-name"))
    if element is None:
        raise ValueError("Element with 'data-file-name' not found")

    last_name: Optional[str] = None

    value = element["data-file-name"]
    if isinstance(value, str):
        last_name = value
        last_name = Path(last_name).name

    return last_id, last_name


def download_file(file_id: str, file_name: str) -> None:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    output_path = DOWNLOAD_DIR / file_name

    response = session.get(
        f"{VALIDATOR_URL}/files/{file_id}",
        stream=True,
    )
    response.raise_for_status()

    with output_path.open("wb") as file:
        for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
            if chunk:
                file.write(chunk)


def get_tftp_link(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    split_btn = soup.find("div", class_="split-btn")

    if split_btn is None:
        raise RuntimeError("split-btn not found")

    server_ip = split_btn.get("data-tftp-host")
    file_id = split_btn.get("data-file-id")

    if not server_ip:
        raise RuntimeError("TFTP server IP not found")

    if not file_id:
        raise RuntimeError("TFTP file ID not found")

    tftp_url = f"tftp://{server_ip}/{file_id}"

    return tftp_url
