import time
import json
import asyncio
import subprocess
from datetime import datetime

import requests
from rich.console import Console
from rich.live import Live

from .api import (
    get_latest_file,
    get_tftp_link,
    get_upload_csrf,
    login,
    parse_latest_file,
)
from .ui import ValidatorUI
from .config import variables


console = Console()


async def _ansible_switches(tftp_link: str):
    variables["tftp_link"] = tftp_link

    process = await asyncio.create_subprocess_exec(
        "ansible-playbook",
        "-i",
        "inventory.yml",
        "upgrade.yml",
        "--extra-vars",
        f"tftp_link={tftp_link}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            f"Deploy failed with code {process.returncode}\n{stderr.decode()}"
        )

    return stdout.decode()


def _do_login(ui: ValidatorUI, live: Live) -> None:
    ui.set_status("Logging in", "yellow")
    ui.message = "Authenticating..."

    try:
        login()

    except requests.RequestException as error:
        ui.set_status("Login failed", "red")
        ui.message = str(error)
        ui.add_event("ERROR", f"Login failed: {error}")

        live.update(ui.render())
        time.sleep(2)

        raise

    ui.add_event("INFO", "Login successful")


def _init_state(ui: ValidatorUI, live: Live) -> None:
    try:
        get_upload_csrf()

        html = get_latest_file()

        last_id, last_name = parse_latest_file(html)

        if last_id is None:
            raise RuntimeError("Latest file ID not found")

        if last_name is None:
            raise RuntimeError("Latest file name not found")

    except Exception as error:
        ui.set_status("Initialization failed", "red")
        ui.message = str(error)
        ui.add_event("ERROR", str(error))

        live.update(ui.render())
        time.sleep(2)

        raise

    ui.image_id = last_id
    ui.image_name = last_name

    ui.set_status("Watching", "green")
    ui.message = "Watching for a new image..."

    ui.add_event(
        "INFO",
        f"Current image: {last_name} ({last_id})",
    )

    live.update(ui.render())


async def main() -> None:
    ui = ValidatorUI()

    with Live(
        ui.render(),
        console=console,
        refresh_per_second=4,
        transient=False,
    ) as live:
        _do_login(ui, live)

        _init_state(ui, live)

        # ------------------------------------------------------------------
        # Основной polling loop
        # ------------------------------------------------------------------

        while True:
            ui.next_check = datetime.now()

            for _ in range(30):
                await asyncio.sleep(1)

                ui.next_check = datetime.now()
                live.update(ui.render())

            ui.checks += 1
            ui.last_check = datetime.now()

            try:
                html = await asyncio.to_thread(get_latest_file)

                current_id, current_name = parse_latest_file(html)

                if current_id is None:
                    continue

                if current_id != ui.image_id:
                    ui.image_id = current_id
                    ui.image_name = current_name

                    tftp_link = get_tftp_link(html)
                    ui.tftp_link = tftp_link

                    ui.set_status("New image", "bold green")
                    ui.message = f"New image detected: {current_name}"

                    ui.add_event("NEW", f"{current_name} ({current_id})")
                    ui.add_event("INFO", tftp_link)

                    await _ansible_switches(tftp_link)

                    live.update(ui.render())

                    await asyncio.sleep(2)

                    ui.set_status("Watching", "green")
                    ui.message = "Watching for a new image..."

                else:
                    ui.set_status("Watching", "green")
                    ui.message = "No new image"

            except requests.RequestException as error:
                ui.set_status("HTTP error", "red")
                ui.message = str(error)

                ui.add_event("ERROR", f"HTTP: {error}")

            except Exception as error:
                ui.set_status("Error", "red")
                ui.message = str(error)

                ui.add_event("ERROR", str(error))

            live.update(ui.render())
