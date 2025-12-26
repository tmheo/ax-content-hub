"""Summarizer tool for content summarization.

Gemini API를 사용하여 GeekNews 스타일 요약을 생성합니다.
"""

from dataclasses import dataclass, field

from src.adapters.gemini_client import GeminiClient
from src.models.content import Content


@dataclass
class SummaryResult:
    """요약 결과."""

    title_ko: str
    summary_ko: str
    why_important: str
    categories: list[str] = field(default_factory=list)


# 시스템 프롬프트
SUMMARIZER_SYSTEM_PROMPT = """당신은 기술 뉴스 큐레이터입니다.
GeekNews 스타일로 간결하고 핵심적인 요약을 작성합니다.

응답 규칙:
1. title_ko: 20자 이내의 한국어 제목 (핵심 정보만)
2. summary_ko: 3문장 이내의 요약 (무엇, 왜 중요한지, 영향)
3. why_important: AX(AI Transformation) 관점에서의 의미
4. categories: 관련 카테고리 목록 (LLM, Enterprise AI, Automation 등)

JSON 형식으로만 응답하세요."""


def _build_prompt(title_ko: str, body_ko: str | None) -> str:
    """요약 프롬프트 생성."""
    body_section = body_ko if body_ko else "(본문 없음)"

    return f"""다음 콘텐츠를 GeekNews 스타일로 요약해주세요.

## 원본 콘텐츠

**제목**: {title_ko}

**본문**:
{body_section}

## 요청 사항

위 콘텐츠를 다음 JSON 형식으로 요약해주세요:

{{
    "title_ko": "20자 이내 핵심 제목",
    "summary_ko": "3문장 이내 요약",
    "why_important": "AX 관점에서의 중요성",
    "categories": ["카테고리1", "카테고리2"]
}}

반드시 JSON만 응답하세요."""


def _truncate_title(title: str, max_length: int = 20) -> str:
    """제목 길이 제한."""
    if len(title) <= max_length:
        return title
    return title[: max_length - 1] + "…"


def _truncate_summary(summary: str, max_sentences: int = 3) -> str:
    """요약 문장 수 제한."""
    # 마침표로 문장 분리
    sentences = []
    current = ""

    for char in summary:
        current += char
        if char in ".!?。":
            sentences.append(current.strip())
            current = ""

    if current.strip():
        sentences.append(current.strip())

    # 최대 문장 수로 제한
    limited = sentences[:max_sentences]

    return " ".join(limited)


def summarize_content(
    content: Content,
    title_ko: str,
    body_ko: str | None,
    gemini_client: GeminiClient,
    max_retries: int = 2,
) -> SummaryResult:
    """콘텐츠 요약.

    GeekNews 스타일로 요약하고 AX 관련성을 분석합니다.

    Args:
        content: 원본 콘텐츠.
        title_ko: 번역된 제목.
        body_ko: 번역된 본문.
        gemini_client: Gemini 클라이언트.
        max_retries: JSON 파싱 재시도 횟수.

    Returns:
        요약 결과.

    Raises:
        ValueError: 요약 실패.
    """
    prompt = _build_prompt(title_ko, body_ko)
    last_error: Exception | None = None

    for _attempt in range(max_retries):
        try:
            result = gemini_client.generate_json(
                prompt=prompt,
                system_prompt=SUMMARIZER_SYSTEM_PROMPT,
                max_retries=1,  # 내부 재시도는 1회
            )

            # 필수 필드 확인
            if not all(
                k in result for k in ["title_ko", "summary_ko", "why_important"]
            ):
                raise ValueError("Missing required fields in response")

            # 제목 및 요약 길이 제한 적용
            title = _truncate_title(result["title_ko"])
            summary = _truncate_summary(result["summary_ko"])

            return SummaryResult(
                title_ko=title,
                summary_ko=summary,
                why_important=result["why_important"],
                categories=result.get("categories", []),
            )

        except (ValueError, KeyError) as e:
            last_error = e
            continue

    raise ValueError(f"Failed to summarize after {max_retries} attempts: {last_error}")
