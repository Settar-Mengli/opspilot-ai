"""Run the API with a Windows-compatible event loop for psycopg async."""

from __future__ import annotations

import asyncio
import sys


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    import uvicorn

    uvicorn.run(
        "opspilot.api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        app_dir="src",
    )


if __name__ == "__main__":
    main()
