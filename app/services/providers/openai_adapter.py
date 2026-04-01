import base64

from openai import AsyncOpenAI

from app.schemas.events import AudioChunkEvent


class OpenAIAdapter:
    def __init__(
        self,
        api_key: str,
        stt_model: str,
        translation_model: str,
        tts_model: str,
        tts_voice: str,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._stt_model = stt_model
        self._translation_model = translation_model
        self._tts_model = tts_model
        self._tts_voice = tts_voice

    async def transcribe_chunk(
        self,
        event: AudioChunkEvent,
        chunk_index: int,
        context_text: str | None = None,
    ) -> str:
        audio_bytes = base64.b64decode(event.chunk)
        content_type = event.content_type.split(";", 1)[0].strip().lower()
        extension = self._extension_for_content_type(content_type)
        transcription = await self._client.audio.transcriptions.create(
            file=(f"chunk-{chunk_index}.{extension}", audio_bytes, content_type),
            model=self._stt_model,
            language=event.source_language,
            prompt=context_text or "",
            response_format="text",
        )
        return str(transcription).strip()

    async def translate(self, text: str, source_language: str, target_language: str) -> str:
        source_name = self._language_name(source_language)
        target_name = self._language_name(target_language)
        response = await self._client.responses.create(
            model=self._translation_model,
            instructions=(
                "You are a realtime interpreter for business calls. "
                "Translate naturally, preserve meaning, keep numbers and names accurate, "
                "and return only the translated text."
            ),
            input=f"Translate from {source_name} to {target_name}: {text}",
        )
        output_text = getattr(response, "output_text", "")
        if output_text:
            return output_text.strip()

        # Defensive fallback for SDK response shape differences.
        if hasattr(response, "output") and response.output:
            parts: list[str] = []
            for item in response.output:
                content = getattr(item, "content", None) or []
                for block in content:
                    text_value = getattr(block, "text", None)
                    if text_value:
                        parts.append(text_value)
            if parts:
                return "\n".join(parts).strip()

        raise ValueError("Translation response did not contain text output.")

    async def synthesize(self, text: str, language: str, preferred_voice: str | None) -> str:
        voice = preferred_voice or self._tts_voice
        language_name = self._language_name(language)
        response = await self._client.audio.speech.create(
            model=self._tts_model,
            voice=voice,
            input=text,
            instructions=(
                f"Speak naturally in {language_name}. Keep pacing clear and concise for real-time translation."
            ),
            response_format="mp3",
        )
        audio_bytes = await response.aread()
        return base64.b64encode(audio_bytes).decode("utf-8")

    @staticmethod
    def _extension_for_content_type(content_type: str) -> str:
        return {
            "audio/webm": "webm",
            "audio/wav": "wav",
            "audio/wave": "wav",
            "audio/mp4": "mp4",
            "audio/mpeg": "mp3",
            "audio/mp3": "mp3",
            "audio/ogg": "ogg",
        }.get(content_type, "webm")

    @staticmethod
    def _language_name(language_code: str) -> str:
        return {
            "en": "English",
            "hi": "Hindi",
            "pa": "Punjabi",
        }.get(language_code, language_code)
