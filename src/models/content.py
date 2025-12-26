"""Content model for collected and processed content.

수집/처리된 콘텐츠를 관리합니다.
"""

import hashlib
from datetime import datetime
from enum import Enum
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import BaseModel, Field, field_validator

# 추적 파라미터 목록
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "ref_src",
    "fbclid",
    "gclid",
    "source",
}


def normalize_url(url: str) -> str:
    """URL 정규화 (멱등성 키 생성용).

    Rules:
    - scheme/host 소문자화
    - trailing '/' 제거
    - 추적 파라미터 제거 (utm_*, ref, fbclid, etc.)
    - fragment 제거
    """
    parsed = urlparse(url.lower())
    query = parse_qs(parsed.query)

    # 추적 파라미터 제거
    filtered_query = {k: v for k, v in query.items() if k not in TRACKING_PARAMS}

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/") or "/",
            "",
            urlencode(filtered_query, doseq=True),
            "",  # fragment 제거
        )
    ).rstrip("/")


def generate_content_key(source_id: str, url: str) -> str:
    """콘텐츠 멱등성 키 생성.

    Format: {source_id}:{sha256(normalized_url)[:16]}
    """
    normalized = normalize_url(url)
    url_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"{source_id}:{url_hash}"


class ProcessingStatus(str, Enum):
    """콘텐츠 처리 상태."""

    PENDING = "pending"  # 수집됨, 처리 대기
    PROCESSING = "processing"  # 처리 중
    COMPLETED = "completed"  # 처리 완료
    FAILED = "failed"  # 처리 실패
    SKIPPED = "skipped"  # 건너뜀 (예: 자막 없음)
    TIMEOUT = "timeout"  # 타임아웃


class Content(BaseModel):
    """수집/처리된 콘텐츠.

    Firestore Collection: contents
    """

    id: str = Field(..., description="고유 ID")
    source_id: str = Field(..., description="소스 참조")

    # 멱등성 키 (중복 방지)
    content_key: str = Field(..., description="{source_id}:{sha256(normalized_url)}")

    # 원본 정보
    original_url: str = Field(..., description="원문 URL")
    original_title: str = Field(..., description="원문 제목")
    original_body: str | None = Field(None, description="원문 본문 (YouTube: 자막)")
    original_language: str = Field("en", description="원문 언어")
    original_published_at: datetime | None = Field(None, description="원문 발행일")

    # 처리 결과 (번역/요약)
    title_ko: str | None = Field(
        None, max_length=20, description="한국어 제목 (20자 이내)"
    )
    summary_ko: str | None = Field(None, description="한국어 요약 (3문장)")
    why_important: str | None = Field(None, description="중요성 설명 (1문장)")

    # 스코어링
    relevance_score: float | None = Field(
        None, ge=0.0, le=1.0, description="AX 관련성 (0.0~1.0)"
    )
    categories: list[str] = Field(
        default_factory=list, description="자동 분류된 카테고리"
    )

    # 처리 상태
    processing_status: ProcessingStatus = Field(
        ProcessingStatus.PENDING, description="처리 상태"
    )
    processing_attempts: int = Field(0, ge=0, description="처리 시도 횟수")
    last_error: str | None = Field(None, description="마지막 에러 메시지")

    # 타임스탬프
    collected_at: datetime = Field(..., description="수집 시간")
    processed_at: datetime | None = Field(None, description="처리 완료 시간")

    @field_validator("title_ko")
    @classmethod
    def validate_title_ko_length(cls, v: str | None) -> str | None:
        """title_ko 최대 길이 검증."""
        if v is not None and len(v) > 20:
            raise ValueError("title_ko must be 20 characters or less")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "cnt_abc123",
                "source_id": "src_001",
                "content_key": "src_001:a1b2c3d4e5f6",
                "original_url": "https://openai.com/blog/gpt-5",
                "original_title": "Introducing GPT-5",
                "title_ko": "GPT-5 공개: 추론 능력 향상",
                "summary_ko": "OpenAI가 GPT-5를 공개했습니다.",
                "relevance_score": 0.95,
                "processing_status": "completed",
            }
        }
    }
