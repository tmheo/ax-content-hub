"""Subscriptions CRUD API endpoints.

구독 관리 API입니다.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.adapters.firestore_client import FirestoreClient
from src.config.settings import Settings
from src.models.subscription import (
    DeliveryFrequency,
    Subscription,
    SubscriptionPreferences,
)
from src.repositories.subscription_repo import SubscriptionRepository

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


class PlatformConfigRequest(BaseModel):
    """플랫폼 설정 요청."""

    team_id: str = Field(..., description="Slack 팀 ID")
    channel_id: str = Field(..., description="Slack 채널 ID")


class PreferencesRequest(BaseModel):
    """선호도 설정 요청."""

    frequency: DeliveryFrequency = Field(
        DeliveryFrequency.DAILY, description="발송 빈도"
    )
    delivery_time: str = Field("09:00", description="발송 시간 (HH:MM)")
    min_relevance: float = Field(0.3, ge=0.0, le=1.0, description="최소 관련성 점수")
    categories: list[str] = Field(default_factory=list, description="관심 카테고리")
    language: str = Field("ko", description="발송 언어")


class SubscriptionCreateRequest(BaseModel):
    """구독 생성 요청."""

    platform_config: PlatformConfigRequest = Field(..., description="플랫폼 설정")
    preferences: PreferencesRequest | None = None


class PreferencesUpdateRequest(BaseModel):
    """선호도 수정 요청 (부분 수정 가능)."""

    frequency: DeliveryFrequency | None = None
    delivery_time: str | None = None
    min_relevance: float | None = None
    categories: list[str] | None = None
    language: str | None = None


class SubscriptionUpdateRequest(BaseModel):
    """구독 수정 요청."""

    preferences: PreferencesUpdateRequest | None = None


class SubscriptionListResponse(BaseModel):
    """구독 목록 응답."""

    subscriptions: list[dict[str, Any]]
    total: int


def get_subscription_repo(request: Request | None = None) -> SubscriptionRepository:
    """SubscriptionRepository 인스턴스 생성."""
    if request and hasattr(request.app.state, "firestore"):
        firestore = request.app.state.firestore
    else:
        settings = Settings()  # type: ignore[call-arg]
        firestore = FirestoreClient(project_id=settings.GCP_PROJECT_ID)

    return SubscriptionRepository(firestore)


@router.get("")
async def list_subscriptions(
    request: Request,
    active: bool | None = None,
) -> SubscriptionListResponse:
    """구독 목록 조회.

    Args:
        request: FastAPI 요청 객체
        active: 활성화 상태 필터

    Returns:
        구독 목록
    """
    repo = get_subscription_repo(request)

    if active is True:
        subscriptions = repo.find_active_subscriptions()
    else:
        subscriptions = repo.find_all()

    return SubscriptionListResponse(
        subscriptions=[s.model_dump(mode="json") for s in subscriptions],
        total=len(subscriptions),
    )


@router.get("/{subscription_id}")
async def get_subscription(
    request: Request,
    subscription_id: str,
) -> dict[str, Any]:
    """단일 구독 조회.

    Args:
        request: FastAPI 요청 객체
        subscription_id: 구독 ID

    Returns:
        구독 정보
    """
    repo = get_subscription_repo(request)
    subscription = repo.get_by_id(subscription_id)

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return subscription.model_dump(mode="json")


@router.post("", status_code=201)
async def create_subscription(
    request: Request,
    body: SubscriptionCreateRequest,
) -> dict[str, Any]:
    """새 구독 생성.

    Args:
        request: FastAPI 요청 객체
        body: 구독 생성 요청

    Returns:
        생성된 구독 정보
    """
    repo = get_subscription_repo(request)
    now = datetime.now(UTC)

    # 선호도 설정
    if body.preferences:
        preferences = SubscriptionPreferences(
            frequency=body.preferences.frequency,
            delivery_time=body.preferences.delivery_time,
            min_relevance=body.preferences.min_relevance,
            categories=body.preferences.categories,
            language=body.preferences.language,
        )
    else:
        preferences = SubscriptionPreferences()

    subscription = Subscription(
        id=f"sub_{uuid4().hex[:8]}",
        platform="slack",
        platform_config={
            "team_id": body.platform_config.team_id,
            "channel_id": body.platform_config.channel_id,
        },
        preferences=preferences,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    repo.create(subscription)

    logger.info(
        "subscription_created",
        subscription_id=subscription.id,
        channel_id=body.platform_config.channel_id,
    )

    return subscription.model_dump(mode="json")


@router.put("/{subscription_id}")
async def update_subscription(
    request: Request,
    subscription_id: str,
    body: SubscriptionUpdateRequest,
) -> dict[str, Any]:
    """구독 수정.

    Args:
        request: FastAPI 요청 객체
        subscription_id: 구독 ID
        body: 구독 수정 요청

    Returns:
        수정된 구독 정보
    """
    repo = get_subscription_repo(request)
    subscription = repo.get_by_id(subscription_id)

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # 업데이트할 필드만 적용
    now = datetime.now(UTC)

    if body.preferences:
        # 기존 preferences를 복사하고 새 값으로 업데이트
        current_prefs = subscription.preferences.model_dump()

        if body.preferences.frequency is not None:
            current_prefs["frequency"] = body.preferences.frequency.value
        if body.preferences.delivery_time is not None:
            current_prefs["delivery_time"] = body.preferences.delivery_time
        if body.preferences.min_relevance is not None:
            current_prefs["min_relevance"] = body.preferences.min_relevance
        if body.preferences.categories is not None:
            current_prefs["categories"] = body.preferences.categories
        if body.preferences.language is not None:
            current_prefs["language"] = body.preferences.language

        subscription.preferences = SubscriptionPreferences(**current_prefs)

    subscription.updated_at = now

    repo.update(subscription)

    logger.info("subscription_updated", subscription_id=subscription_id)

    return subscription.model_dump(mode="json")


@router.delete("/{subscription_id}", status_code=204)
async def delete_subscription(
    request: Request,
    subscription_id: str,
) -> None:
    """구독 삭제.

    Args:
        request: FastAPI 요청 객체
        subscription_id: 구독 ID
    """
    repo = get_subscription_repo(request)
    subscription = repo.get_by_id(subscription_id)

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    repo.delete(subscription_id)

    logger.info("subscription_deleted", subscription_id=subscription_id)


@router.post("/{subscription_id}/activate")
async def activate_subscription(
    request: Request,
    subscription_id: str,
) -> dict[str, Any]:
    """구독 활성화.

    Args:
        request: FastAPI 요청 객체
        subscription_id: 구독 ID

    Returns:
        활성화된 구독 정보
    """
    repo = get_subscription_repo(request)
    subscription = repo.get_by_id(subscription_id)

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    repo.activate(subscription_id)
    subscription.is_active = True
    subscription.updated_at = datetime.now(UTC)

    logger.info("subscription_activated", subscription_id=subscription_id)

    return subscription.model_dump(mode="json")


@router.post("/{subscription_id}/deactivate")
async def deactivate_subscription(
    request: Request,
    subscription_id: str,
) -> dict[str, Any]:
    """구독 비활성화.

    Args:
        request: FastAPI 요청 객체
        subscription_id: 구독 ID

    Returns:
        비활성화된 구독 정보
    """
    repo = get_subscription_repo(request)
    subscription = repo.get_by_id(subscription_id)

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    repo.deactivate(subscription_id)
    subscription.is_active = False
    subscription.updated_at = datetime.now(UTC)

    logger.info("subscription_deactivated", subscription_id=subscription_id)

    return subscription.model_dump(mode="json")
