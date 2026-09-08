"""Models used by the voice streaming API."""

from pydantic import BaseModel


class VoiceTokenResponse(BaseModel):
    """Short-lived credentials used to open the browser voice stream."""

    token: str