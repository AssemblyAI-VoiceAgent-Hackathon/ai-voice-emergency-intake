"""Models used by the voice streaming API."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class VoiceTokenResponse(BaseModel):
    """Short-lived credentials used to open the browser voice stream."""

    token: str


class TranscriptTurn(BaseModel):
    turnId: Optional[str] = None
    speaker: Optional[str] = None
    text: Optional[str] = None
    spokenAt: Optional[str] = None
    final: bool = True


class VoiceHandoffRequest(BaseModel):
    """Closed-session turns that Role 2 wraps into intake-transcript.schema.json."""

    caseId: Optional[str] = None
    sessionId: Optional[str] = None
    caseVersion: int = 1
    language: Optional[str] = "en"
    turns: list[TranscriptTurn] = Field(default_factory=list)
    observations: list[dict[str, Any]] = Field(default_factory=list)
    verifiedRecords: list[dict[str, Any]] = Field(default_factory=list)
