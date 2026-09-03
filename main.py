#!/usr/bin/env python3

import asyncio
import sys
from datetime import datetime
import time

from src import Flasher, UI, POLL_INTERVAL


async def main():
    main_app = Flasher()
    ui = UI(main_app)

    while True:
        for _ in range(POLL_INTERVAL):
            await main_app.run()
            ui.render()

            for _ in range(POLL_INTERVAL * 10):
                await asyncio.sleep(0.1)
                ui.refresh()


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [INFO] Stopped by user.")

    except Exception as error:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [FATAL] {error}")
        sys.exit(1)
