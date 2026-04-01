from typing import Protocol


class TranslationService(Protocol):
    async def translate(self, text: str, target_language: str) -> str: ...


class MockTranslationService:
    MOCK_TRANSLATIONS = {
        "en": "This is a demo English translation.",
        "hi": "यह एक डेमो हिंदी अनुवाद है।",
        "pa": "ਇਹ ਇੱਕ ਡੈਮੋ ਪੰਜਾਬੀ ਅਨੁਵਾਦ ਹੈ।",
    }

    async def translate(self, text: str, target_language: str) -> str:
        translated = self.MOCK_TRANSLATIONS.get(
            target_language, f"Demo translation for {target_language}."
        )
        return f"{translated} Source: {text}"
