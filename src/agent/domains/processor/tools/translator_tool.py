"""Translator tool for content translation.

Gemini API를 사용하여 콘텐츠를 번역합니다.
"""

from dataclasses import dataclass

from src.adapters.gemini_client import GeminiClient
from src.models.content import Content

# 번역할 본문 최대 길이 (Gemini 컨텍스트 제한 고려)
MAX_BODY_LENGTH = 30000


@dataclass
class TranslationResult:
    """번역 결과."""

    title_ko: str
    body_ko: str | None
    source_language: str
    target_language: str


def translate_content(
    content: Content,
    gemini_client: GeminiClient,
    target_lang: str = "ko",
) -> TranslationResult:
    """콘텐츠 번역.

    원본 언어가 대상 언어와 같으면 번역을 건너뜁니다.

    Args:
        content: 번역할 콘텐츠.
        gemini_client: Gemini 클라이언트.
        target_lang: 대상 언어 코드 (기본: "ko").

    Returns:
        번역 결과.

    Raises:
        Exception: 번역 실패.
    """
    source_lang = content.original_language

    # 원본 언어와 대상 언어가 같으면 번역 건너뜀
    if source_lang == target_lang:
        return TranslationResult(
            title_ko=content.original_title,
            body_ko=content.original_body,
            source_language=source_lang,
            target_language=target_lang,
        )

    # 제목 번역
    title_ko = gemini_client.translate(
        text=content.original_title,
        target_lang=target_lang,
        source_lang=source_lang,
    )

    # 본문 번역 (있는 경우)
    body_ko = None
    if content.original_body:
        # 긴 본문 잘라내기
        body_text = content.original_body
        if len(body_text) > MAX_BODY_LENGTH:
            body_text = body_text[:MAX_BODY_LENGTH]

        body_ko = gemini_client.translate(
            text=body_text,
            target_lang=target_lang,
            source_lang=source_lang,
        )

    return TranslationResult(
        title_ko=title_ko,
        body_ko=body_ko,
        source_language=source_lang,
        target_language=target_lang,
    )
