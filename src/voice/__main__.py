"""Run Role 1: python -m src.voice

Puts src/voice on sys.path so the existing `app.*` imports resolve without
colliding with the Next.js `app/` directory at the repository root.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

VOICE_ROOT = Path(__file__).resolve().parent
if str(VOICE_ROOT) not in sys.path:
    sys.path.insert(0, str(VOICE_ROOT))

from app.core.assemblyai import load_env  # noqa: E402
from app.main import app  # noqa: E402


def main() -> None:
    import uvicorn

    load_env()
    host = os.environ.get("ARIA_VOICE_BIND_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", os.environ.get("ARIA_VOICE_BIND_PORT", "8001")))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
