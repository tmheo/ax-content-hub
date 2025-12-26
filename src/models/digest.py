"""Digest model for sent digests.

발송된 다이제스트를 기록하여 중복 발송을 방지합니다.
"""

import re
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class DigestStatus(str, Enum):
    """다이제스트 상태."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


def generate_digest_key(subscription_id: str, digest_date: date) -> str:
    """다이제스트 멱등성 키 생성.

    Format: {subscription_id}:{YYYY-MM-DD}
    """
    return f"{subscription_id}:{digest_date.isoformat()}"


class Digest(BaseModel):
    """발송된 다이제스트 이력.

    Firestore Collection: digests
    """

    id: str = Field(..., description="고유 ID")
    subscription_id: str = Field(..., description="구독 참조")

    # 멱등성 키 (일일 중복 방지)
    digest_key: str = Field(..., description="{subscription_id}:{YYYY-MM-DD}")
    digest_date: date = Field(..., description="다이제스트 날짜")

    # 콘텐츠 참조
    content_ids: list[str] = Field(..., description="포함된 콘텐츠 ID 목록")
    content_count: int = Field(..., ge=0, description="콘텐츠 개수")

    # 발송 대상
    channel_id: str = Field(..., description="슬랙 채널 ID")

    # 상태 관리
    status: DigestStatus = Field(
        default=DigestStatus.PENDING, description="다이제스트 상태"
    )
    created_at: datetime = Field(..., description="생성 시간")
    sent_at: datetime | None = Field(None, description="발송 시간")
    slack_message_ts: str | None = Field(
        None, description="슬랙 메시지 타임스탬프 (수정/삭제용)"
    )
    error: str | None = Field(None, description="에러 메시지")

    @model_validator(mode="after")
    def validate_digest(self) -> "Digest":
        """다이제스트 검증."""
        # digest_key 형식 검증: {subscription_id}:{YYYY-MM-DD}
        pattern = r"^[\w-]+:\d{4}-\d{2}-\d{2}$"
        if not re.match(pattern, self.digest_key):
            raise ValueError(
                "digest_key must be in format '{subscription_id}:{YYYY-MM-DD}'"
            )

        # content_count와 content_ids 길이 일치
        if self.content_count != len(self.content_ids):
            raise ValueError(
                f"content_count ({self.content_count}) must match "
                f"content_ids length ({len(self.content_ids)})"
            )

        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "dig_001",
                "subscription_id": "sub_001",
                "digest_key": "sub_001:2025-12-26",
                "digest_date": "2025-12-26",
                "content_ids": ["cnt_abc123", "cnt_def456"],
                "content_count": 2,
                "channel_id": "C123456789",
                "status": "pending",
                "created_at": "2025-12-26T08:00:00Z",
                "sent_at": "2025-12-26T09:00:15Z",
                "slack_message_ts": "1735203615.000100",
            }
        }
    }
