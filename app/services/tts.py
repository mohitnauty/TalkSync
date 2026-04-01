import base64
from typing import Protocol


class TextToSpeechService(Protocol):
    async def synthesize(
        self, text: str, language: str, preferred_voice: str | None = None
    ) -> str: ...


class MockTextToSpeechService:
    async def synthesize(
        self, text: str, language: str, preferred_voice: str | None = None
    ) -> str:
        voice = preferred_voice or "default"
        payload = f"{language}:{voice}:{text}".encode("utf-8")
        return base64.b64encode(payload).decode("utf-8")
