"""Routes for starting a voice streaming session."""

from typing import Union

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.voice import VoiceTokenResponse
from app.services.voice_service import VoiceService, VoiceServiceError

router = APIRouter(prefix="/api/voice", tags=["voice"])
voice_service = VoiceService()


@router.get("/token", response_model=VoiceTokenResponse)
def token() -> Union[VoiceTokenResponse, JSONResponse]:
    """Return a short-lived token for the browser voice websocket."""
    try:
        return VoiceTokenResponse(token=voice_service.create_token())
    except VoiceServiceError as error:
        return JSONResponse(
            {"error": "token request failed"},
            status_code=502,
        )