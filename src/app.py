import time
import asyncio
from datetime import datetime

import requests

from .api import (
    get_latest_file,
    get_tftp_link,
    get_upload_csrf,
    login,
    parse_latest_file,
)
from .config import (
    ANSIBLE_COMMAND_TIMEOUT,
    ANSIBLE_INVENTORY,
    ANSIBLE_PLAYBOOK,
    POST_UPGRADE_DELAY,
    POLL_GRANULARITY,
    POLL_INTERVAL,
    RETRY_DELAY,
    SWITCH_HOST,
    TFTP_SERVER_IP,
    SWITCH_USERNAME,
    ANSIBLE_PASSWORD,
)


def log(level: str, message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {message}", flush=True)


async def _ansible_switches(tftp_link: str):
    process = await asyncio.create_subprocess_exec(
        "ansible-playbook",
        "-i",
        ANSIBLE_INVENTORY,
        ANSIBLE_PLAYBOOK,
        "--extra-vars",
        f"tftp_link={tftp_link} \
        switch_host={SWITCH_HOST} \
        tftp_server_ip={TFTP_SERVER_IP} \
        switch_username={SWITCH_USERNAME} \
        ansible_password={ANSIBLE_PASSWORD} \
        ansible_command_timeout={ANSIBLE_COMMAND_TIMEOUT}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            f"Deploy failed with code {process.returncode}\n{stderr.decode()}"
        )

    return stdout.decode()


def _do_login() -> None:
    log("INFO", "Logging in...")

    try:
        login()
    except requests.RequestException as error:
        log("ERROR", f"Login failed: {error}")
        time.sleep(RETRY_DELAY)
        raise

    log("INFO", "Login successful")


def _init_state() -> tuple:
    log("INFO", "Initializing...")

    try:
        get_upload_csrf()
        html = get_latest_file()
        last_id, last_name = parse_latest_file(html)

        if last_id is None:
            raise RuntimeError("Latest file ID not found")

        if last_name is None:
            raise RuntimeError("Latest file name not found")

    except Exception as error:
        log("ERROR", str(error))
        time.sleep(RETRY_DELAY)
        raise

    log("INFO", f"Current image: {last_name} ({last_id})")
    return last_id, last_name


async def main() -> None:
    _do_login()

    image_id, image_name = _init_state()

    log("INFO", "Watching for a new image...")

    while True:
        for _ in range(POLL_INTERVAL):
            await asyncio.sleep(POLL_GRANULARITY)

        try:
            html = await asyncio.to_thread(get_latest_file)
            current_id, current_name = parse_latest_file(html)

            if current_id is None:
                continue

            if current_id != image_id:
                image_id = current_id
                image_name = current_name

                tftp_link = get_tftp_link(html)

                log("NEW", f"New image: {current_name} ({current_id})")
                log("INFO", f"TFTP: {tftp_link}")

                await _ansible_switches(tftp_link)

                await asyncio.sleep(POST_UPGRADE_DELAY)

                log("INFO", "Watching for a new image...")

            else:
                log("INFO", "No new image")

        except requests.RequestException as error:
            log("ERROR", f"HTTP: {error}")

        except Exception as error:
            log("ERROR", str(error))
