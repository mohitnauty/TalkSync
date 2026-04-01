from typing import Protocol

from app.schemas.events import AudioChunkEvent


class SpeechToTextService(Protocol):
    async def transcribe_chunk(
        self,
        event: AudioChunkEvent,
        chunk_index: int,
        context_text: str | None = None,
    ) -> str: ...


class MockSpeechToTextService:
    async def transcribe_chunk(
        self,
        event: AudioChunkEvent,
        chunk_index: int,
        context_text: str | None = None,
    ) -> str:
        preview = event.chunk[:16]
        return (
            f"English transcript chunk {chunk_index} "
            f"from {event.content_type} payload {preview}"
        )
