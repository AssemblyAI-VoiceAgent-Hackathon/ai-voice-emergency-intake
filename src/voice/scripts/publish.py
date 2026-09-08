"""Publish the configured AssemblyAI agent: python -m scripts.publish"""

from __future__ import annotations

import os
import sys
from pathlib import Path

VOICE_ROOT = Path(__file__).resolve().parents[1]
if str(VOICE_ROOT) not in sys.path:
    sys.path.insert(0, str(VOICE_ROOT))

from app.core.assemblyai import load_env, publish_agent, read_agent  # noqa: E402


def main() -> None:
    load_env()
    name = os.environ.get("AGENT", "emergency-voice")
    agent = read_agent(name)
    result = publish_agent(agent, name=name, reuse_by_name=True)
    verb = "Created" if result["created"] else "Updated"
    print(f'{verb} agent {result["id"]} ({name})')
    if result.get("saved"):
        print(f"Saved id to {result['key']}")


if __name__ == "__main__":
    main()
