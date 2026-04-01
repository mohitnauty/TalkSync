import pytest

from app.schemas.events import AudioChunkEvent, JoinSessionEvent, SessionConfig
from app.core.config import get_settings
from app.services.orchestrator import RealtimeOrchestrator


@pytest.fixture(autouse=True)
def force_mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "your_real_openai_api_key")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_audio_chunk_generates_caption_translation_and_audio() -> None:
    orchestrator = RealtimeOrchestrator()
    session = await orchestrator.create_session()
    _ = [
        response
        async for response in orchestrator.handle_event(
        session.session_id,
        JoinSessionEvent(
            participant_id="listener-1",
            role="listener",
            preferred_language="hi",
            session_config=SessionConfig(target_language="hi", channel="web"),
        ),
    )]

    responses = [
        response
        async for response in orchestrator.handle_event(
        session.session_id,
        AudioChunkEvent(
            chunk="dGVzdC1hdWRpby1jaHVuaw==",
            participant_id="listener-1",
            source_language="en",
            target_language="hi",
        ),
    )]

    assert len(responses) == 4
    assert responses[0].event == "caption"
    assert responses[1].event == "translation"
    assert responses[2].event == "session_state"
    assert responses[3].event == "audio"


@pytest.mark.asyncio
async def test_join_session_tracks_participant_preferences() -> None:
    orchestrator = RealtimeOrchestrator()
    session = await orchestrator.create_session()

    responses = [
        response
        async for response in orchestrator.handle_event(
        session.session_id,
        JoinSessionEvent(
            participant_id="client-1",
            role="client",
            preferred_language="pa",
            session_config=SessionConfig(
                source_language="en",
                target_language="pa",
                auto_detect_language=True,
                detected_language="en",
                channel="zoom",
                ai_tier="free",
            ),
        ),
    )]

    assert responses[0].event == "participant_joined"
    assert responses[1].event == "session_state"
