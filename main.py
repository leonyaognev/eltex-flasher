#!/usr/bin/env python3

import sys

from rich.console import Console

from src.app import main

console = Console()

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
