"""AssemblyAI operations used by voice routes."""

from app.core.assemblyai import ApiError, aai


class VoiceServiceError(Exception):
    """Raised when a voice stream cannot be initialized."""

    def __init__(self, error: ApiError):
        super().__init__(str(error))
        self.status = error.status


class VoiceService:
    """Create credentials for browser-to-AssemblyAI voice streams."""

    def create_token(self) -> str:
        try:
            result = aai("/token?product=voice_agent&expires_in_seconds=60")
        except ApiError as error:
            raise VoiceServiceError(error) from error
        return result["token"]