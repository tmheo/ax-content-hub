"""Internal tasks endpoints for Cloud Tasks callbacks.

Cloud Tasks에서 호출되는 개별 비동기 작업 핸들러입니다.
/internal/tasks/* 경로는 Cloud Run IAM + OIDC 토큰으로 보호됩니다.
"""

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.adapters.firestore_client import FirestoreClient
from src.adapters.gemini_client import GeminiClient
from src.adapters.slack_client import SlackClient
from src.config.settings import Settings
from src.repositories.content_repo import ContentRepository
from src.repositories.digest_repo import DigestRepository
from src.repositories.source_repo import SourceRepository
from src.repositories.subscription_repo import SubscriptionRepository
from src.services.content_pipeline import ContentPipeline
from src.services.digest_service import DigestService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/internal/tasks", tags=["tasks"])


class ProcessContentRequest(BaseModel):
    """콘텐츠 처리 요청."""

    content_id: str


class SendDigestRequest(BaseModel):
    """다이제스트 발송 요청."""

    digest_id: str


class CollectSourceRequest(BaseModel):
    """소스 수집 요청."""

    source_id: str


def get_content_pipeline(request: Request | None = None) -> ContentPipeline:
    """ContentPipeline 인스턴스 생성."""
    if request and hasattr(request.app.state, "firestore"):
        firestore = request.app.state.firestore
        settings = request.app.state.settings
    else:
        settings = Settings()  # type: ignore[call-arg]
        firestore = FirestoreClient(project_id=settings.GCP_PROJECT_ID)

    source_repo = SourceRepository(firestore)
    content_repo = ContentRepository(firestore)
    gemini_client = GeminiClient(api_key=settings.GOOGLE_API_KEY)

    return ContentPipeline(
        source_repo=source_repo,
        content_repo=content_repo,
        gemini_client=gemini_client,
    )


def get_digest_service(request: Request | None = None) -> DigestService:
    """DigestService 인스턴스 생성."""
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


def get_content_repo(request: Request | None = None) -> ContentRepository:
    """ContentRepository 인스턴스 생성."""
    if request and hasattr(request.app.state, "firestore"):
        firestore = request.app.state.firestore
    else:
        settings = Settings()  # type: ignore[call-arg]
        firestore = FirestoreClient(project_id=settings.GCP_PROJECT_ID)

    return ContentRepository(firestore)


def get_digest_repo(request: Request | None = None) -> DigestRepository:
    """DigestRepository 인스턴스 생성."""
    if request and hasattr(request.app.state, "firestore"):
        firestore = request.app.state.firestore
    else:
        settings = Settings()  # type: ignore[call-arg]
        firestore = FirestoreClient(project_id=settings.GCP_PROJECT_ID)

    return DigestRepository(firestore)


def get_source_repo(request: Request | None = None) -> SourceRepository:
    """SourceRepository 인스턴스 생성."""
    if request and hasattr(request.app.state, "firestore"):
        firestore = request.app.state.firestore
    else:
        settings = Settings()  # type: ignore[call-arg]
        firestore = FirestoreClient(project_id=settings.GCP_PROJECT_ID)

    return SourceRepository(firestore)


@router.post("/process")
async def process_content_task(
    request: Request,
    body: ProcessContentRequest,
) -> dict[str, Any]:
    """단일 콘텐츠 처리 태스크.

    Cloud Tasks에서 개별 콘텐츠 처리를 위해 호출됩니다.
    원래 설계: /internal/tasks/process

    Args:
        request: FastAPI 요청 객체
        body: 콘텐츠 ID를 포함한 요청 본문

    Returns:
        처리 결과
    """
    content_repo = get_content_repo(request)
    content = content_repo.get_by_id(body.content_id)

    if not content:
        raise HTTPException(
            status_code=404,
            detail=f"Content not found: {body.content_id}",
        )

    try:
        pipeline = get_content_pipeline(request)
        success = pipeline._process_single_content(content)

        if success:
            logger.info(
                "content_task_completed",
                content_id=body.content_id,
            )
            return {
                "status": "success",
                "content_id": body.content_id,
            }
        else:
            logger.error(
                "content_task_failed",
                content_id=body.content_id,
            )
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "error": "Content processing failed"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "content_task_error",
            content_id=body.content_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "error": str(e)},
        ) from e


@router.post("/send-digest")
async def send_digest_task(
    request: Request,
    body: SendDigestRequest,
) -> dict[str, Any]:
    """단일 다이제스트 발송 태스크.

    Cloud Tasks에서 개별 다이제스트 발송을 위해 호출됩니다.

    Args:
        request: FastAPI 요청 객체
        body: 다이제스트 ID를 포함한 요청 본문

    Returns:
        발송 결과
    """
    digest_repo = get_digest_repo(request)
    digest = digest_repo.get_by_id(body.digest_id)

    if not digest:
        raise HTTPException(
            status_code=404,
            detail=f"Digest not found: {body.digest_id}",
        )

    try:
        service = get_digest_service(request)
        success = service.send_digest(digest)

        if success:
            logger.info(
                "digest_task_completed",
                digest_id=body.digest_id,
            )
            return {
                "status": "success",
                "digest_id": body.digest_id,
            }
        else:
            logger.error(
                "digest_task_failed",
                digest_id=body.digest_id,
            )
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "error": "Digest sending failed"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "digest_task_error",
            digest_id=body.digest_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "error": str(e)},
        ) from e


@router.post("/collect-source")
async def collect_source_task(
    request: Request,
    body: CollectSourceRequest,
) -> dict[str, Any]:
    """단일 소스 수집 태스크.

    Cloud Tasks에서 개별 소스 수집을 위해 호출됩니다.

    Args:
        request: FastAPI 요청 객체
        body: 소스 ID를 포함한 요청 본문

    Returns:
        수집 결과
    """
    source_repo = get_source_repo(request)
    source = source_repo.get_by_id(body.source_id)

    if not source:
        raise HTTPException(
            status_code=404,
            detail=f"Source not found: {body.source_id}",
        )

    try:
        pipeline = get_content_pipeline(request)
        content_ids = pipeline._collect_from_source(source)

        logger.info(
            "source_task_completed",
            source_id=body.source_id,
            collected=len(content_ids),
        )

        return {
            "status": "success",
            "source_id": body.source_id,
            "collected": len(content_ids),
        }
    except Exception as e:
        logger.error(
            "source_task_error",
            source_id=body.source_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "error": str(e)},
        ) from e
