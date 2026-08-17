#!/usr/bin/env python3

import os
import re
import time
import signal
import sys
from datetime import datetime
from pathlib import Path
from collections import deque

import requests
import urllib3
from bs4 import BeautifulSoup

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


URL = "https://validator-v2.eltex.loc"
DOWNLOAD_DIR = Path.home() / "work_pc"

VALIDATOR_USER = os.environ["VALIDATOR_USER"]
VALIDATOR_PASSWORD = os.environ["VALIDATOR_PASSWORD"]

session = requests.Session()

# Аналог curl -ks
session.verify = False

# Убираем InsecureRequestWarning из-за verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console()


def get_csrf_from_login():
    response = session.get(f"{URL}/login/")
    response.raise_for_status()

    match = re.search(
        r'name="csrf_token"\s+value="([^"]+)"',
        response.text,
    )

    if not match:
        raise RuntimeError("CSRF token not found")

    return match.group(1)


def login():
    csrf_token = get_csrf_from_login()

    response = session.post(
        f"{URL}/login/",
        data={
            "login": VALIDATOR_USER,
            "password": VALIDATOR_PASSWORD,
            "csrf_token": csrf_token,
        },
    )
    response.raise_for_status()


def get_upload_csrf():
    response = session.get(f"{URL}/files/")
    response.raise_for_status()

    match = re.search(
        r'<meta\s+name="csrf-token"\s+content="([^"]+)"',
        response.text,
    )

    if not match:
        raise RuntimeError("Upload CSRF token not found")

    return match.group(1)


def get_latest_file():
    response = session.get(f"{URL}/files/")
    response.raise_for_status()

    return response.text


def parse_latest_file(html):
    soup = BeautifulSoup(html, "html.parser")

    last_id = None

    for td in soup.find_all("td"):
        text = td.get_text(strip=True)

        if text.isdigit():
            last_id = text
            break

    element = soup.find(attrs={"data-file-name": True})

    if element is None:
        last_name = None
    else:
        last_name = element["data-file-name"]
        last_name = Path(last_name).name

    return last_id, last_name


def download_file(file_id, file_name):
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    output_path = DOWNLOAD_DIR / file_name

    response = session.get(
        f"{URL}/files/{file_id}",
        stream=True,
    )
    response.raise_for_status()

    with output_path.open("wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
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


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------


class ValidatorUI:
    def __init__(self):
        self.status = "Starting"
        self.status_style = "yellow"

        self.image_id = None
        self.image_name = None
        self.tftp_link = None

        self.checks = 0
        self.last_check = None
        self.next_check = None

        self.message = "Initializing..."
        self.message_style = "dim"

        self.events = deque(maxlen=8)

    def add_event(self, level: str, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")

        self.events.append(
            (
                timestamp,
                level,
                message,
            )
        )

    def set_status(self, status: str, style: str):
        self.status = status
        self.status_style = style

    def render(self):
        # ------------------------------------------------------------------
        # Верхняя информация
        # ------------------------------------------------------------------

        info = Table.grid(padding=(0, 2))
        info.add_column(style="bold cyan", width=14)
        info.add_column()

        info.add_row("Status", Text(f"● {self.status}", style=self.status_style))

        info.add_row("Validator", Text(URL, style="dim"))

        info.add_row(
            "Image ID", Text(str(self.image_id) if self.image_id else "—", style="bold")
        )

        info.add_row("Image", Text(self.image_name or "—", style="bold"))

        info.add_row(
            "Last check",
            (self.last_check.strftime("%H:%M:%S") if self.last_check else "—"),
        )

        info.add_row(
            "Next check",
            (self.next_check.strftime("%H:%M:%S") if self.next_check else "—"),
        )

        info.add_row(
            "Checks",
            str(self.checks),
        )

        if self.tftp_link:
            info.add_row(
                "TFTP",
                Text(self.tftp_link, style="bold green"),
            )

        # ------------------------------------------------------------------
        # События
        # ------------------------------------------------------------------

        events = Table(
            expand=True,
            box=None,
            padding=(0, 1),
        )

        events.add_column("TIME", style="dim", width=10)
        events.add_column("LEVEL", width=8)
        events.add_column("MESSAGE")

        level_styles = {
            "INFO": "cyan",
            "NEW": "bold green",
            "WARN": "yellow",
            "ERROR": "bold red",
        }

        for timestamp, level, message in reversed(self.events):
            events.add_row(
                timestamp, Text(level, style=level_styles.get(level, "white")), message
            )

        if not self.events:
            events.add_row("—", "—", Text("No events yet", style="dim"))

        status_panel = Panel(
            info,
            title="[bold]ELTEX Validator[/bold]",
            subtitle=self.message,
            border_style=self.status_style,
            padding=(1, 2),
        )

        events_panel = Panel(
            events, title="[bold]Events[/bold]", border_style="dim", padding=(0, 1)
        )

        root = Table.grid()
        root.add_row(status_panel)
        root.add_row(events_panel)

        return root


def main():
    ui = ValidatorUI()

    # ----------------------------------------------------------------------
    # Login
    # ----------------------------------------------------------------------

    ui.set_status("Logging in", "yellow")
    ui.message = "Authenticating..."

    with Live(
        ui.render(),
        console=console,
        refresh_per_second=4,
        transient=False,
    ) as live:
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

        # ------------------------------------------------------------------
        # Initial state
        # ------------------------------------------------------------------

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

        # ------------------------------------------------------------------
        # Основной polling loop
        # ------------------------------------------------------------------

        while True:
            # Показываем время следующей проверки.
            ui.next_check = datetime.now()

            for _ in range(10):
                time.sleep(1)

                # Обновляем UI каждую секунду, чтобы таймер не выглядел мёртвым.
                ui.next_check = datetime.now()

                live.update(ui.render())

            ui.checks += 1
            ui.last_check = datetime.now()
            ui.next_check = datetime.now()

            try:
                html = get_latest_file()

                current_id, current_name = parse_latest_file(html)

                if current_id is None:
                    ui.set_status("Warning", "yellow")
                    ui.message = "Current file ID not found"
                    ui.add_event(
                        "WARN",
                        "Current file ID not found",
                    )

                    live.update(ui.render())
                    continue

                # ----------------------------------------------------------
                # Новое изображение
                # ----------------------------------------------------------

                if current_id != ui.image_id:
                    ui.image_id = current_id
                    ui.image_name = current_name

                    tftp_link = get_tftp_link(html)

                    ui.tftp_link = tftp_link

                    ui.set_status("New image", "bold green")
                    ui.message = f"New image detected: {current_name}"

                    ui.add_event(
                        "NEW",
                        f"{current_name} ({current_id})",
                    )

                    ui.add_event(
                        "INFO",
                        tftp_link,
                    )

                    live.update(ui.render())

                    # После отображения события возвращаем обычный статус.
                    time.sleep(2)

                    ui.set_status("Watching", "green")
                    ui.message = "Watching for a new image..."

                # ----------------------------------------------------------
                # Ничего нового
                # ----------------------------------------------------------

                else:
                    ui.set_status("Watching", "green")
                    ui.message = "No new image"

            except requests.RequestException as error:
                ui.set_status("HTTP error", "red")
                ui.message = str(error)

                ui.add_event(
                    "ERROR",
                    f"HTTP: {error}",
                )

            except Exception as error:
                ui.set_status("Error", "red")
                ui.message = str(error)

                ui.add_event(
                    "ERROR",
                    str(error),
                )

            live.update(ui.render())


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        console.print()
        console.print("[bold yellow]Stopped by user.[/bold yellow]")

    except Exception as error:
        console.print()
        console.print(f"[bold red]Fatal error:[/bold red] {error}")
        sys.exit(1)
