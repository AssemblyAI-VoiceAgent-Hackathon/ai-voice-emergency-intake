"""Role 3 authenticated FastAPI backend.

Owns structured-case ingestion, SSE live updates, staff-review submission,
tool calling, and the Role 4 persistence handoff.
"""

from .app import create_app

__all__ = ["create_app"]
