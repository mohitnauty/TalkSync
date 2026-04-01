from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter


LanguageCode = Literal["en", "hi", "pa"]
ParticipantRole = Literal["speaker", "listener", "client", "agent", "supervisor"]
ChannelName = Literal["web", "zoom", "google_meet", "microsoft_teams", "zoho_meeting"]
AiTier = Literal["free", "paid"]


class SessionConfig(BaseModel):
    source_language: LanguageCode = "en"
    target_language: LanguageCode = "hi"
    detected_language: LanguageCode | None = None
    auto_detect_language: bool = True
    translation_enabled: bool = True
    transcript_enabled: bool = False
    audio_output_enabled: bool = True
    ai_tier: AiTier = "free"
    preferred_voice: str | None = None
    channel: ChannelName = "web"


class JoinSessionEvent(BaseModel):
    event: Literal["join_session"] = "join_session"
    participant_id: str
    participant_name: str | None = None
    role: ParticipantRole = "listener"
    preferred_language: LanguageCode | None = None
    receive_audio: bool = True
    receive_transcript: bool = True
    session_config: SessionConfig = Field(default_factory=SessionConfig)


class AudioChunkEvent(BaseModel):
    event: Literal["audio_chunk"] = "audio_chunk"
    chunk: str = Field(..., description="Base64 encoded audio chunk.")
    content_type: str = "audio/webm"
    participant_id: str | None = None
    source_language: LanguageCode = "en"
    target_language: LanguageCode = "hi"


class TextChunkEvent(BaseModel):
    event: Literal["text_chunk"] = "text_chunk"
    text: str
    participant_id: str | None = None
    source_language: LanguageCode = "en"
    target_language: LanguageCode = "hi"


class SessionStartedEvent(BaseModel):
    event: Literal["session_started"] = "session_started"
    session_id: str
    supported_languages: list[LanguageCode]
    supported_channels: list[ChannelName]
    ai_tier: AiTier = "free"
    provider_mode: Literal["mock", "openai"] = "mock"


class ParticipantJoinedEvent(BaseModel):
    event: Literal["participant_joined"] = "participant_joined"
    session_id: str
    participant_id: str
    role: ParticipantRole
    preferred_language: LanguageCode
    channel: ChannelName


class CaptionEvent(BaseModel):
    event: Literal["caption"] = "caption"
    session_id: str
    participant_id: str | None = None
    text: str
    language: LanguageCode
    is_final: bool = False


class TranslationEvent(BaseModel):
    event: Literal["translation"] = "translation"
    session_id: str
    participant_id: str | None = None
    text: str
    language: LanguageCode
    is_final: bool = False


class AudioEvent(BaseModel):
    event: Literal["audio"] = "audio"
    session_id: str
    participant_id: str | None = None
    audio_base64: str
    content_type: str = "audio/mp3"
    language: LanguageCode
    is_final: bool = False


class SessionStateEvent(BaseModel):
    event: Literal["session_state"] = "session_state"
    session_id: str
    participant_count: int
    active_channel: ChannelName
    source_language: LanguageCode
    target_language: LanguageCode
    transcript_enabled: bool
    audio_output_enabled: bool


class ErrorEvent(BaseModel):
    event: Literal["error"] = "error"
    code: int
    message: str


ClientEvent = Annotated[
    JoinSessionEvent | AudioChunkEvent | TextChunkEvent,
    Field(discriminator="event"),
]
ServerEvent = Annotated[
    SessionStartedEvent
    | ParticipantJoinedEvent
    | SessionStateEvent
    | CaptionEvent
    | TranslationEvent
    | AudioEvent
    | ErrorEvent,
    Field(discriminator="event"),
]

client_event_adapter = TypeAdapter(ClientEvent)
