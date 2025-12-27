"""Scheduler endpoints for Cloud Scheduler triggers.

Cloud Scheduler에 의해 호출되는 내부 엔드포인트입니다.
/internal/* 경로는 Cloud Run IAM + OIDC 토큰으로 보호됩니다.
"""

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request

from src.adapters.firestore_client import FirestoreClient
from src.adapters.gemini_client import GeminiClient
from src.adapters.slack_client import SlackClient
from src.adapters.tasks_client import TasksClient
from src.config.settings import Settings
from src.repositories.content_repo import ContentRepository
from src.repositories.digest_repo import DigestRepository
from src.repositories.source_repo import SourceRepository
from src.repositories.subscription_repo import SubscriptionRepository
from src.services.content_pipeline import ContentPipeline
from src.services.digest_service import DigestService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/internal", tags=["scheduler"])


def get_content_pipeline(request: Request | None = None) -> ContentPipeline:
    """ContentPipeline 인스턴스 생성.

    Args:
        request: FastAPI 요청 객체 (app.state 접근용)

    Returns:
        ContentPipeline 인스턴스
    """
    if request and hasattr(request.app.state, "firestore"):
        firestore = request.app.state.firestore
        settings = request.app.state.settings
        tasks_client = getattr(request.app.state, "tasks", None)
    else:
        settings = Settings()  # type: ignore[call-arg]
        firestore = FirestoreClient(project_id=settings.GCP_PROJECT_ID)
        # 로컬에서는 direct 모드로 TasksClient 생성
        tasks_client = TasksClient(mode=settings.TASKS_MODE)

    source_repo = SourceRepository(firestore)
    content_repo = ContentRepository(firestore)
    gemini_client = GeminiClient(api_key=settings.GOOGLE_API_KEY)

    return ContentPipeline(
        source_repo=source_repo,
        content_repo=content_repo,
        gemini_client=gemini_client,
        tasks_client=tasks_client,
    )


def get_digest_service(request: Request | None = None) -> DigestService:
    """DigestService 인스턴스 생성.

    Args:
        request: FastAPI 요청 객체 (app.state 접근용)

    Returns:
        DigestService 인스턴스
    """
    if request and hasattr(request.app.state, "firestore"):
        firestore = request.app.state.firestore
        settings = request.app.state.settings
        slack_client = request.app.state.slack
    else:
        settings = Settings()  # type: ignore[call-arg]
        firestore = FirestoreClient(project_id=settings.GCP_PROJECT_ID)
        slack_client = SlackClient(token=settings.SLACK_BOT_TOKEN)

    content_repo = ContentRepository(firestore)
    digest_repo = DigestRepository(firestore)
    subscription_repo = SubscriptionRepository(firestore)

    return DigestService(
        content_repo=content_repo,
        digest_repo=digest_repo,
        subscription_repo=subscription_repo,
        slack_client=slack_client,
    )


@router.post("/collect")
async def collect_content(request: Request) -> dict[str, Any]:
    """콘텐츠 수집 트리거.

    Cloud Scheduler에서 1시간마다 호출됩니다.
    수집 후 각 콘텐츠에 대해 Cloud Tasks로 처리 작업을 enqueue합니다.
    TASKS_MODE=direct일 경우 즉시 처리됩니다.

    Returns:
        수집 결과 통계 (total_sources, collected, enqueued, errors)
    """
    try:
        pipeline = get_content_pipeline(request)
        result = pipeline.collect_from_sources()

        logger.info(
            "content_collection_completed",
            total_sources=result["total_sources"],
            collected=result["collected"],
            enqueued=result.get("enqueued", 0),
            errors=result.get("errors", 0),
        )

        return {
            "status": "success",
            "result": result,
        }
    except Exception as e:
        logger.error("content_collection_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "error": str(e)},
        ) from e


@router.post("/distribute")
async def distribute_digests(request: Request) -> dict[str, Any]:
    """다이제스트 생성 및 발송 트리거.

    Cloud Scheduler에서 매일 09:00 KST에 호출됩니다.
    활성 구독에 대해 다이제스트를 생성하고 슬랙으로 발송합니다.

    Returns:
        발송 결과 통계
    """
    from datetime import date

    try:
        service = get_digest_service(request)
        today = date.today()

        # 활성 구독 조회
        subscriptions = service.subscription_repo.find_active_subscriptions()

        result = {
            "total_subscriptions": len(subscriptions),
            "created": 0,
            "sent": 0,
            "skipped": 0,
            "failed": 0,
        }

        for subscription in subscriptions:
            try:
                # 다이제스트 생성 및 발송
                digest = service.create_digest(subscription, today)

                # 이미 발송된 다이제스트인지 확인
                if digest.status.value == "sent":
                    result["skipped"] += 1
                    continue

                result["created"] += 1

                # 발송
                success = service.send_digest(digest)
                if success:
                    result["sent"] += 1
                else:
                    result["failed"] += 1

            except Exception as e:
                logger.error(
                    "subscription_digest_failed",
                    subscription_id=subscription.id,
                    error=str(e),
                )
                result["failed"] += 1

        logger.info(
            "digest_distribution_completed",
            total_subscriptions=result["total_subscriptions"],
            created=result["created"],
            sent=result["sent"],
            skipped=result["skipped"],
            failed=result["failed"],
        )

        return {
            "status": "success",
            "result": result,
        }
    except Exception as e:
        logger.error("digest_distribution_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "error": str(e)},
        ) from e
