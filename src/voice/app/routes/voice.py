"""Routes for starting a voice streaming session."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.voice import VoiceHandoffRequest, VoiceTokenResponse
from app.services.voice_service import VoiceService, VoiceServiceError
from src.voice.handoff import handoff_transcript

_EXAMPLE = (
    Path(__file__).resolve().parents[4] / "contracts" / "examples" / "intake-transcript.example.json"
)

router = APIRouter(prefix="/api/voice", tags=["voice"])
voice_service = VoiceService()


@router.get("/token", response_model=VoiceTokenResponse)
def token() -> Union[VoiceTokenResponse, JSONResponse]:
    """Return a short-lived token for the browser voice websocket."""
    try:
        return VoiceTokenResponse(token=voice_service.create_token())
    except VoiceServiceError:
        return JSONResponse(
            {"error": "token request failed"},
            status_code=502,
        )


@router.post("/handoff")
def handoff(body: VoiceHandoffRequest) -> JSONResponse:
    """Sanitize turns, run Role 2 extraction, and ingest the case into Role 3."""
    try:
        result = handoff_transcript(body.model_dump())
    except ValueError as error:
        return JSONResponse(
            {
                "error": {
                    "code": "EMPTY_TRANSCRIPT",
                    "message": str(error),
                }
            },
            status_code=422,
        )
    extraction = result.get("extraction") or {}
    if extraction.get("status") != "success":
        return JSONResponse(result, status_code=422)
    ingest = result.get("ingest") or {}
    code = ingest.get("httpStatus")
    if code == 0:
        return JSONResponse(result, status_code=503)
    if code in (200, 202):
        return JSONResponse(result, status_code=202)
    return JSONResponse(result, status_code=502)


@router.post("/demo-intake")
def demo_intake() -> JSONResponse:
    """Run the frozen synthetic transcript through Role 2 and Role 3."""
    example = json.loads(_EXAMPLE.read_text(encoding="utf-8"))
    result = handoff_transcript(example)
    extraction = result.get("extraction") or {}
    if extraction.get("status") != "success":
        return JSONResponse(result, status_code=422)
    ingest = result.get("ingest") or {}
    if ingest.get("httpStatus") == 0:
        return JSONResponse(result, status_code=503)
    if ingest.get("httpStatus") in (200, 202):
        return JSONResponse(result, status_code=202)
    return JSONResponse(result, status_code=502)