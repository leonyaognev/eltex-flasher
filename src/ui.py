from collections import deque
from datetime import datetime
from typing import Optional

from rich.align import Align
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import URL


class ValidatorUI:
    def __init__(self) -> None:
        self.status: str = "Starting"
        self.status_style: str = "yellow"

        self.image_id: Optional[str] = None
        self.image_name: Optional[str] = None
        self.tftp_link: Optional[str] = None

        self.checks: int = 0
        self.last_check: Optional[datetime] = None
        self.next_check: Optional[datetime] = None

        self.message: str = "Initializing..."
        self.message_style: str = "dim"

        self.events: deque[tuple[str, str, str]] = deque(maxlen=8)

    def add_event(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")

        self.events.append(
            (
                timestamp,
                level,
                message,
            )
        )

    def set_status(self, status: str, style: str) -> None:
        self.status = status
        self.status_style = style

    def render(self) -> Align:
        info = Table.grid(padding=(0, 2))

        info.add_column(style="bold cyan", width=14, no_wrap=True)
        info.add_column(no_wrap=True)

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
        info.add_row("Checks", str(self.checks))

        if self.tftp_link:
            info.add_row("TFTP", Text(self.tftp_link, style="bold green"))

        events = Table(expand=True, box=None, padding=(0, 1))

        events.add_column("TIME", style="dim", width=10, no_wrap=True)
        events.add_column("LEVEL", width=8, no_wrap=True)
        events.add_column("MESSAGE", no_wrap=True)

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
            subtitle=Text(self.message, style=self.message_style),
            border_style=self.status_style,
            padding=(1, 2),
        )

        events_panel = Panel(
            events, title="[bold]Events[/bold]", border_style="dim", padding=(0, 1)
        )

        root = Table.grid(padding=(1, 0))

        root.add_row(status_panel)
        root.add_row(events_panel)

        return Align.center(root, vertical="middle")


class ValidatorApp:
    def __init__(self) -> None:
        self.ui = ValidatorUI()

        self.live = Live(
            self.ui.render(),
            refresh_per_second=10,
            transient=True,
        )

    def start(self) -> None:
        with self.live:
            self.run()

    def update(self) -> None:
        self.live.update(
            self.ui.render(),
        )

    def run(self) -> None:
        self.ui.set_status(
            "Running",
            "green",
        )

        self.ui.message = "Validator is running..."

        self.ui.add_event(
            "INFO",
            "Validator started",
        )

        self.update()


def main() -> None:
    app = ValidatorApp()
    app.start()


if __name__ == "__main__":
    main()
