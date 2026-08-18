#!/usr/bin/env python3

import asyncio
import sys
from datetime import datetime

from src.app import main

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
