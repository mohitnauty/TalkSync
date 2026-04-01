from dataclasses import dataclass, field
from typing import AsyncIterator
from uuid import uuid4

from app.core.config import get_settings
from app.schemas.events import (
    AudioEvent,
    AudioChunkEvent,
    CaptionEvent,
    ClientEvent,
    JoinSessionEvent,
    ParticipantJoinedEvent,
    ServerEvent,
    SessionConfig,
    SessionStateEvent,
    TextChunkEvent,
    TranslationEvent,
)
from app.services.providers.openai_adapter import OpenAIAdapter
from app.services.stt import MockSpeechToTextService
from app.services.translation import MockTranslationService
from app.services.tts import MockTextToSpeechService


DEFAULT_SUPPORTED_LANGUAGES = ["en", "hi", "pa"]
DEFAULT_SUPPORTED_CHANNELS = ["web", "zoom", "google_meet", "microsoft_teams"]


@dataclass
class ParticipantState:
    participant_id: str
    role: str
    preferred_language: str
    receive_audio: bool = True
    receive_transcript: bool = True
    preferred_voice: str | None = None


@dataclass
class SessionState:
    session_id: str
    transcript_parts: list[str] = field(default_factory=list)
    last_target_language: str = "hi"
    source_language: str = "en"
    channel: str = "web"
    ai_tier: str = "free"
    transcript_enabled: bool = False
    audio_output_enabled: bool = True
    participants: dict[str, ParticipantState] = field(default_factory=dict)


class RealtimeOrchestrator:
    def __init__(self) -> None:
        settings = get_settings()
        self._sessions: dict[str, SessionState] = {}
        self._provider_mode = "mock"
        self._stt_service = MockSpeechToTextService()
        self._translation_service = MockTranslationService()
        self._tts_service = MockTextToSpeechService()

        if settings.has_real_openai_key:
            openai_adapter = OpenAIAdapter(
                api_key=settings.openai_api_key,
                stt_model=settings.stt_model,
                translation_model=settings.translation_model,
                tts_model=settings.tts_model,
                tts_voice=settings.tts_voice,
            )
            self._provider_mode = "openai"
            self._stt_service = openai_adapter
            self._translation_service = openai_adapter
            self._tts_service = openai_adapter

    @property
    def provider_mode(self) -> str:
        return self._provider_mode

    async def create_session(self) -> SessionState:
        session_id = str(uuid4())
        session = SessionState(session_id=session_id)
        self._sessions[session_id] = session
        return session

    async def handle_event(
        self, session_id: str, event: ClientEvent
    ) -> AsyncIterator[ServerEvent]:
        session = self._sessions[session_id]

        if isinstance(event, JoinSessionEvent):
            for response in self._handle_join(session, event):
                yield response
            return

        if isinstance(event, AudioChunkEvent):
            participant = self._resolve_participant(session, event.participant_id)
            source_language = (
                session.source_language if event.source_language == "en" else event.source_language
            )
            target_language = participant.preferred_language
            session.last_target_language = target_language
            chunk_index = len(session.transcript_parts) + 1
            transcript_context = self._build_transcript_context(session)
            transcript_text = await self._stt_service.transcribe_chunk(
                event, chunk_index, transcript_context
            )
            session.transcript_parts.append(transcript_text)
            translated_text = await self._translate_text(
                transcript_text, source_language, target_language
            )
            yield CaptionEvent(
                session_id=session_id,
                participant_id=participant.participant_id,
                text=transcript_text,
                is_final=False,
                language=source_language,
            )
            yield TranslationEvent(
                session_id=session_id,
                participant_id=participant.participant_id,
                text=translated_text,
                language=target_language,
                is_final=False,
            )
            yield SessionStateEvent(
                session_id=session_id,
                participant_count=len(session.participants),
                active_channel=session.channel,
                source_language=session.source_language,
                target_language=target_language,
                transcript_enabled=session.transcript_enabled,
                audio_output_enabled=session.audio_output_enabled,
            )

            if participant.receive_audio and session.audio_output_enabled:
                audio_base64 = await self._tts_service.synthesize(
                    translated_text, target_language, participant.preferred_voice
                )
                yield AudioEvent(
                    session_id=session_id,
                    participant_id=participant.participant_id,
                    audio_base64=audio_base64,
                    language=target_language,
                    is_final=False,
                )

            return

        if isinstance(event, TextChunkEvent):
            participant = self._resolve_participant(session, event.participant_id)
            source_language = event.source_language
            target_language = participant.preferred_language
            session.last_target_language = target_language
            transcript_text = event.text.strip()
            if not transcript_text:
                return
            session.transcript_parts.append(transcript_text)
            translated_text = await self._translate_text(
                transcript_text, source_language, target_language
            )
            yield CaptionEvent(
                session_id=session_id,
                participant_id=participant.participant_id,
                text=transcript_text,
                is_final=False,
                language=source_language,
            )
            yield TranslationEvent(
                session_id=session_id,
                participant_id=participant.participant_id,
                text=translated_text,
                language=target_language,
                is_final=False,
            )
            yield SessionStateEvent(
                session_id=session_id,
                participant_count=len(session.participants),
                active_channel=session.channel,
                source_language=session.source_language,
                target_language=target_language,
                transcript_enabled=session.transcript_enabled,
                audio_output_enabled=session.audio_output_enabled,
            )
            return

    async def close_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def _handle_join(
        self, session: SessionState, event: JoinSessionEvent
    ) -> list[ServerEvent]:
        config: SessionConfig = event.session_config
        preferred_language = event.preferred_language or config.target_language

        session.source_language = config.detected_language or config.source_language
        session.last_target_language = config.target_language
        session.channel = config.channel
        session.ai_tier = config.ai_tier
        session.transcript_enabled = config.transcript_enabled
        session.audio_output_enabled = config.audio_output_enabled
        session.participants[event.participant_id] = ParticipantState(
            participant_id=event.participant_id,
            role=event.role,
            preferred_language=preferred_language,
            receive_audio=event.receive_audio,
            receive_transcript=event.receive_transcript,
            preferred_voice=config.preferred_voice,
        )

        return [
            ParticipantJoinedEvent(
                session_id=session.session_id,
                participant_id=event.participant_id,
                role=event.role,
                preferred_language=preferred_language,
                channel=config.channel,
            ),
            SessionStateEvent(
                session_id=session.session_id,
                participant_count=len(session.participants),
                active_channel=session.channel,
                source_language=session.source_language,
                target_language=session.last_target_language,
                transcript_enabled=session.transcript_enabled,
                audio_output_enabled=session.audio_output_enabled,
            ),
        ]

    def _resolve_participant(
        self, session: SessionState, participant_id: str | None
    ) -> ParticipantState:
        if participant_id and participant_id in session.participants:
            return session.participants[participant_id]

        fallback = session.participants.get("default_listener")
        if fallback:
            return fallback

        participant = ParticipantState(
            participant_id=participant_id or "default_listener",
            role="listener",
            preferred_language=session.last_target_language,
        )
        session.participants[participant.participant_id] = participant
        return participant

    async def _translate_text(
        self, text: str, source_language: str, target_language: str
    ) -> str:
        if self._provider_mode == "openai":
            return await self._translation_service.translate(
                text, source_language, target_language
            )
        return await self._translation_service.translate(text, target_language)

    def _build_transcript_context(self, session: SessionState) -> str:
        if not session.transcript_parts:
            return ""
        return "Previous transcript context:\n" + "\n".join(session.transcript_parts[-3:])
