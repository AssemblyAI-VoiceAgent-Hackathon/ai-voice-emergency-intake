"""Run the Role 3 API: python -m src.backend"""

from __future__ import annotations

import os

import uvicorn

from .app import create_app


def main() -> None:
    host = os.environ.get("ARIA_BIND_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", os.environ.get("ARIA_BIND_PORT", "8000")))
    uvicorn.run(create_app(), host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
