"""Scorer tool for AX relevance scoring.

Gemini API를 사용하여 콘텐츠의 AX 관련성 점수를 계산합니다.
"""

from dataclasses import dataclass

from src.adapters.gemini_client import GeminiClient
from src.models.content import Content


@dataclass
class ScoringResult:
    """스코어링 결과."""

    content_id: str
    score: float


# 시스템 프롬프트
SCORER_SYSTEM_PROMPT = """당신은 AX(AI Transformation) 콘텐츠 관련성 평가 전문가입니다.

콘텐츠가 기업의 AI 도입 및 디지털 전환에 얼마나 유용한지 0.0~1.0 점수로 평가합니다.

평가 기준:
- 1.0: 핵심 AX 전략, 기업 AI 도입 사례, 실무 적용 가이드
- 0.7~0.9: AI/ML 기술 발전, 도구, 프레임워크, 업계 동향
- 0.4~0.6: 일반 기술 뉴스, 간접적 관련성
- 0.1~0.3: 관련성 낮음, 단순 흥미 위주
- 0.0: AX와 무관

숫자만 응답하세요 (예: 0.85)."""


def _build_scoring_prompt(
    summary_ko: str,
    why_important: str,
    categories: list[str] | None = None,
) -> str:
    """스코어링 프롬프트 생성."""
    categories_text = ""
    if categories:
        categories_text = f"\n**카테고리**: {', '.join(categories)}"

    return f"""다음 콘텐츠의 AX 관련성 점수를 0.0~1.0 사이로 평가해주세요.

**요약**: {summary_ko}

**중요성**: {why_important}{categories_text}

숫자만 응답해주세요."""


def score_relevance(
    content: Content,
    summary_ko: str,
    why_important: str,
    gemini_client: GeminiClient,
    categories: list[str] | None = None,
) -> ScoringResult:
    """AX 관련성 점수 계산.

    Args:
        content: 스코어링할 콘텐츠.
        summary_ko: 한국어 요약.
        why_important: 중요성 설명.
        gemini_client: Gemini 클라이언트.
        categories: 카테고리 목록.

    Returns:
        스코어링 결과.

    Raises:
        ValueError: 점수 파싱 실패.
    """
    prompt = _build_scoring_prompt(
        summary_ko=summary_ko,
        why_important=why_important,
        categories=categories,
    )

    score = gemini_client.generate_score(
        prompt=prompt,
        system_prompt=SCORER_SYSTEM_PROMPT,
    )

    # 0.0~1.0 범위로 클램핑 (이미 GeminiClient에서 처리하지만 안전을 위해)
    score = max(0.0, min(1.0, score))

    return ScoringResult(
        content_id=content.id,
        score=score,
    )
