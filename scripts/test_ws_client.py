import asyncio
import json

import websockets


async def main() -> None:
    uri = "ws://127.0.0.1:8000/ws/realtime"

    async with websockets.connect(uri) as websocket:
        print("CONNECTED")
        print(await websocket.recv())

        await websocket.send(
            json.dumps(
                {
                    "event": "join_session",
                    "participant_id": "client-1",
                    "participant_name": "Test Client",
                    "role": "client",
                    "preferred_language": "hi",
                    "receive_audio": True,
                    "receive_transcript": True,
                    "session_config": {
                        "source_language": "en",
                        "target_language": "hi",
                        "detected_language": "en",
                        "auto_detect_language": True,
                        "translation_enabled": True,
                        "transcript_enabled": False,
                        "audio_output_enabled": True,
                        "ai_tier": "free",
                        "channel": "web",
                    },
                }
            )
        )

        print(await websocket.recv())
        print(await websocket.recv())

        await websocket.send(
            json.dumps(
                {
                    "event": "audio_chunk",
                    "participant_id": "client-1",
                    "chunk": "dGVzdC1hdWRpby1jaHVuaw==",
                    "content_type": "audio/webm",
                    "source_language": "en",
                    "target_language": "hi",
                }
            )
        )

        for _ in range(4):
            print(await websocket.recv())


if __name__ == "__main__":
    asyncio.run(main())
