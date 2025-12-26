"""Subscription model for channel subscriptions.

슬랙 채널별 구독 설정을 관리합니다.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class DeliveryFrequency(str, Enum):
    """발송 빈도."""

    REALTIME = "realtime"  # 즉시 발송 (Phase 2+)
    DAILY = "daily"  # 일일 다이제스트
    WEEKLY = "weekly"  # 주간 다이제스트 (Phase 2+)


class SubscriptionPreferences(BaseModel):
    """구독 선호도 설정."""

    frequency: DeliveryFrequency = Field(
        DeliveryFrequency.DAILY, description="발송 빈도"
    )
    delivery_time: str = Field("09:00", description="발송 시간 (HH:MM 형식, KST)")
    categories: list[str] = Field(
        default_factory=list, description="관심 카테고리 (빈 = 전체)"
    )
    min_relevance: float = Field(0.3, ge=0.0, le=1.0, description="최소 관련성 점수")
    language: str = Field("ko", description="발송 언어")

    @field_validator("delivery_time")
    @classmethod
    def validate_delivery_time_format(cls, v: str) -> str:
        """delivery_time HH:MM 형식 검증."""
        pattern = r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$"
        if not re.match(pattern, v):
            raise ValueError("delivery_time must be in HH:MM format (00:00-23:59)")
        return v


class Subscription(BaseModel):
    """슬랙 채널 구독 설정.

    Firestore Collection: subscriptions
    """

    id: str = Field(..., description="고유 ID")
    platform: str = Field("slack", description="플랫폼 (Phase 1: slack만)")

    # 슬랙 설정
    platform_config: dict[str, Any] = Field(
        ..., description="플랫폼 설정 (team_id, channel_id)"
    )

    # 회사 연결 (Phase 3+ 맞춤화용)
    company_id: str | None = Field(None, description="회사 ID")

    # 선호도
    preferences: SubscriptionPreferences = Field(
        default_factory=SubscriptionPreferences, description="구독 선호도"
    )

    # 상태
    is_active: bool = Field(True, description="활성화 여부")

    # 메타데이터
    created_at: datetime = Field(..., description="생성 시간")
    updated_at: datetime = Field(..., description="수정 시간")

    @model_validator(mode="after")
    def validate_platform_config(self) -> "Subscription":
        """platform_config 필수 필드 검증."""
        config = self.platform_config

        # team_id 필수
        if "team_id" not in config:
            raise ValueError("platform_config must contain 'team_id'")

        # channel_id 필수
        if "channel_id" not in config:
            raise ValueError("platform_config must contain 'channel_id'")

        # channel_id는 'C'로 시작 (Slack public/private channel)
        channel_id = config["channel_id"]
        if not channel_id.startswith("C"):
            raise ValueError("channel_id must start with 'C'")

        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "sub_001",
                "platform": "slack",
                "platform_config": {
                    "team_id": "T12345",
                    "channel_id": "C12345",
                },
                "preferences": {
                    "frequency": "daily",
                    "delivery_time": "09:00",
                    "categories": [],
                    "min_relevance": 0.3,
                    "language": "ko",
                },
                "is_active": True,
            }
        }
    }
