"""Source model for content sources.

콘텐츠 소스 (RSS 피드, YouTube 채널 등) 정보를 관리합니다.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    """소스 타입."""

    RSS = "rss"
    YOUTUBE = "youtube"
    WEB = "web"


class Source(BaseModel):
    """콘텐츠 소스 정보.

    Firestore Collection: sources
    """

    id: str = Field(..., description="고유 ID (예: src_001)")
    name: str = Field(..., description="소스 이름 (예: OpenAI Blog)")
    type: SourceType = Field(..., description="소스 타입 (rss/youtube)")
    url: HttpUrl = Field(..., description="피드 URL 또는 채널 URL")

    # 소스별 설정 (선택적)
    config: dict[str, Any] = Field(default_factory=dict, description="타입별 추가 설정")
    category: str | None = Field(None, description="카테고리 (예: AI_RESEARCH)")
    language: str = Field("en", description="원문 언어")

    # 상태 관리
    is_active: bool = Field(True, description="활성화 여부")
    last_fetched_at: datetime | None = Field(None, description="마지막 수집 시간")
    fetch_error_count: int = Field(0, ge=0, description="연속 실패 횟수")

    # 메타데이터
    created_at: datetime = Field(..., description="생성 시간")
    updated_at: datetime = Field(..., description="수정 시간")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "src_001",
                "name": "OpenAI Blog",
                "type": "rss",
                "url": "https://openai.com/blog/rss",
                "category": "AI_RESEARCH",
                "language": "en",
                "is_active": True,
                "last_fetched_at": "2025-12-26T09:00:00Z",
            }
        }
    }
