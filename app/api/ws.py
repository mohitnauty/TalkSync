from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.config import get_settings
from app.schemas.events import ErrorEvent, SessionStartedEvent, client_event_adapter
from app.services.orchestrator import RealtimeOrchestrator

router = APIRouter()
orchestrator = RealtimeOrchestrator()
settings = get_settings()


@router.websocket("/ws/realtime")
async def realtime_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    session = await orchestrator.create_session()

    await websocket.send_json(
        SessionStartedEvent(
            session_id=session.session_id,
            supported_languages=settings.supported_languages,
            supported_channels=settings.supported_channels,
            ai_tier=settings.default_ai_tier,
            provider_mode=orchestrator.provider_mode,
        ).model_dump(mode="json")
    )

    try:
        while True:
            payload = await websocket.receive_json()
            event = client_event_adapter.validate_python(payload)
            async for response in orchestrator.handle_event(session.session_id, event):
                await websocket.send_json(response.model_dump(mode="json"))
    except WebSocketDisconnect:
        await orchestrator.close_session(session.session_id)
    except Exception as exc:
        error = ErrorEvent(
            code=status.WS_1011_INTERNAL_ERROR,
            message=str(exc),
        )
        await websocket.send_json(error.model_dump(mode="json"))
        await orchestrator.close_session(session.session_id)
