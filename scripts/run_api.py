"""Run the API locally."""

from __future__ import annotations


def main() -> None:
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
