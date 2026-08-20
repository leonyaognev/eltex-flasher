from __future__ import annotations

from datetime import datetime, timedelta

from rich.align import Align
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from .app import Flasher
from .config import IMAGE_TO_SWITCH, POLL_INTERVAL


class UI:
    """
    TUI-представление состояния Flasher.

    Ничего не запускает.
    Ничем не управляет.
    Просто получает ссылку на Flasher и отображает
    его текущее состояние.
    """

    def __init__(self, flasher: Flasher) -> None:
        self.flasher = flasher

        self.started_at = datetime.now()

        # Время последнего poll.
        self.last_render = datetime.now()

        # Время следующего poll.
        self.next_poll = self.last_render + timedelta(seconds=POLL_INTERVAL)

        self.live = Live(
            self._build(),
            refresh_per_second=10,
            screen=True,
        )

        self.live.start()

    def render(self) -> None:
        """
        Вызывается из главного цикла main.py.

        Обновляет время следующего poll и интерфейс.
        """

        now = datetime.now()

        self.last_render = now
        self.next_poll = now + timedelta(seconds=POLL_INTERVAL)

        self.live.update(
            self._build(),
            refresh=True,
        )

    def refresh(self) -> None:
        self.live.update(
            self._build(),
            refresh=True,
        )

    def stop(self) -> None:
        self.live.stop()

    def _build(self) -> Group:
        return Group(
            self._header(),
            "",
            self._status(),
            "",
            self._main_grid(),
            "",
            self._footer(),
        )

    def _header(self) -> Panel:
        title = Text()

        title.append(
            "⚡ ELTEX FLASHER\n",
            style="bold bright_magenta",
        )

        title.append(
            "AUTOMATED FIRMWARE DEPLOYMENT CONTROL CENTER",
            style="dim cyan",
        )

        return Panel(
            Align.center(title),
            border_style="bright_magenta",
            padding=(1, 2),
        )

    def _status(self) -> Table:
        table = Table.grid(
            expand=True,
            padding=(0, 1),
        )

        table.add_column()
        table.add_column()
        table.add_column()
        table.add_column()

        tasks_count = len(
            {name: task for name, task in self.flasher.tasks.items() if not task.done()}
        )

        firmware_count = len(self.flasher.IMAGE_NAME_TO_ID)

        validator = Text(
            "● ONLINE",
            style="bold green",
        )

        firmware = (
            Text(
                "● DETECTED",
                style="bold magenta",
            )
            if firmware_count
            else Text(
                "● WAITING",
                style="bold yellow",
            )
        )

        tasks = (
            Text(
                f"● {tasks_count} RUNNING",
                style="bold yellow",
            )
            if tasks_count
            else Text(
                "● IDLE",
                style="bold green",
            )
        )

        uptime = datetime.now() - self.started_at

        table.add_row(
            Panel(
                validator,
                title="VALIDATOR",
                border_style="green",
            ),
            Panel(
                firmware,
                title="FIRMWARE",
                border_style="magenta",
            ),
            Panel(
                tasks,
                title="DEPLOYMENTS",
                border_style=("yellow" if tasks_count else "green"),
            ),
            Panel(
                Text(
                    self._format_uptime(uptime),
                    style="bold cyan",
                ),
                title="UPTIME",
                border_style="cyan",
            ),
        )

        return table

    def _main_grid(self) -> Table:
        table = Table.grid(
            expand=True,
            padding=(0, 1),
        )

        table.add_column(ratio=2)
        table.add_column(ratio=1)

        table.add_row(
            self._firmware_panel(),
            self._deployment_panel(),
        )

        return table

    def _firmware_panel(self) -> Panel:
        table = Table(
            show_header=False,
            expand=True,
            box=None,
            padding=(0, 1),
        )

        table.add_column(
            style="dim",
            width=16,
        )

        table.add_column(
            style="bold white",
        )

        latest = self._latest_image()

        if latest is None:
            table.add_row(
                "STATUS",
                "[yellow]Waiting for image...[/]",
            )

            table.add_row(
                "IMAGE",
                "[dim]-[/]",
            )

            table.add_row(
                "IMAGE ID",
                "[dim]-[/]",
            )

            table.add_row(
                "TARGET",
                "[dim]-[/]",
            )

        else:
            name, image_id = latest

            target = IMAGE_TO_SWITCH.get(
                name,
                "Unknown",
            )

            table.add_row(
                "STATUS",
                "[bold green]READY[/]",
            )

            table.add_row(
                "IMAGE",
                name,
            )

            table.add_row(
                "IMAGE ID",
                str(image_id),
            )

            table.add_row(
                "TARGET",
                target,
            )

        return Panel(
            table,
            title="[bold magenta]LATEST FIRMWARE[/]",
            border_style="magenta",
            padding=(1, 2),
        )

    def _deployment_panel(self) -> Panel:
        active_tasks = {
            name: task for name, task in self.flasher.tasks.items() if not task.done()
        }

        if not active_tasks:
            content = Text(
                "NO ACTIVE DEPLOYMENTS",
                style="bold green",
            )

            return Panel(
                Align.center(content),
                title="[bold cyan]DEPLOYMENT ACTIVITY[/]",
                border_style="cyan",
                padding=(3, 2),
            )

        tasks = Table(
            show_header=False,
            box=None,
            expand=True,
        )

        tasks.add_column()

        for name in active_tasks:
            tasks.add_row(
                f"[yellow]●[/] {name}",
            )

        return Panel(
            tasks,
            title=(f"[bold yellow]{len(active_tasks)} ACTIVE JOBS[/]"),
            border_style="yellow",
            padding=(1, 2),
        )

    def _footer(self) -> Panel:
        progress = Progress(
            TextColumn(
                "[dim]NEXT POLL[/]",
            ),
            BarColumn(),
            TextColumn(
                f"[cyan]{POLL_INTERVAL}s interval[/]",
            ),
            expand=True,
        )

        task = progress.add_task(
            "poll",
            total=POLL_INTERVAL,
        )

        now = datetime.now()

        elapsed = (self.next_poll - now).total_seconds()

        remaining = max(
            0.0,
            min(
                elapsed,
                float(POLL_INTERVAL),
            ),
        )

        completed = POLL_INTERVAL - remaining

        progress.update(
            task,
            completed=completed,
        )

        return Panel(
            progress,
            border_style="bright_black",
        )

    def _latest_image(
        self,
    ) -> tuple[str, str] | None:
        images = self.flasher.IMAGE_NAME_TO_ID

        if not images:
            return None

        name = next(
            reversed(images),
        )

        return (
            name,
            images[name],
        )

    @staticmethod
    def _format_uptime(
        uptime: timedelta,
    ) -> str:
        total = int(
            uptime.total_seconds(),
        )

        hours, remainder = divmod(
            total,
            3600,
        )

        minutes, seconds = divmod(
            remainder,
            60,
        )

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
