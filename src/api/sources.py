"""Sources CRUD API endpoints.

콘텐츠 소스 관리 API입니다.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, HttpUrl

from src.adapters.firestore_client import FirestoreClient
from src.config.settings import Settings
from src.models.source import Source, SourceType
from src.repositories.source_repo import SourceRepository

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceCreateRequest(BaseModel):
    """소스 생성 요청."""

    name: str = Field(..., description="소스 이름")
    type: SourceType = Field(..., description="소스 타입 (rss/youtube)")
    url: HttpUrl = Field(..., description="피드 URL")
    category: str | None = Field(None, description="카테고리")
    language: str = Field("en", description="원문 언어")
    config: dict[str, Any] = Field(default_factory=dict, description="추가 설정")


class SourceUpdateRequest(BaseModel):
    """소스 수정 요청."""

    name: str | None = None
    category: str | None = None
    language: str | None = None
    config: dict[str, Any] | None = None


class SourceListResponse(BaseModel):
    """소스 목록 응답."""

    sources: list[dict[str, Any]]
    total: int


def get_source_repo(request: Request | None = None) -> SourceRepository:
    """SourceRepository 인스턴스 생성."""
    if request and hasattr(request.app.state, "firestore"):
        firestore = request.app.state.firestore
    else:
        settings = Settings()  # type: ignore[call-arg]
        firestore = FirestoreClient(project_id=settings.GCP_PROJECT_ID)

    return SourceRepository(firestore)


@router.get("")
async def list_sources(
    request: Request,
    type: SourceType | None = None,
    active: bool | None = None,
) -> SourceListResponse:
    """소스 목록 조회.

    Args:
        request: FastAPI 요청 객체
        type: 소스 타입 필터
        active: 활성화 상태 필터

    Returns:
        소스 목록
    """
    repo = get_source_repo(request)

    if active is True:
        sources = repo.find_active_sources()
    elif type is not None:
        sources = repo.find_by_type(type)
    else:
        sources = repo.find_all()

    return SourceListResponse(
        sources=[s.model_dump(mode="json") for s in sources],
        total=len(sources),
    )


@router.get("/{source_id}")
async def get_source(
    request: Request,
    source_id: str,
) -> dict[str, Any]:
    """단일 소스 조회.

    Args:
        request: FastAPI 요청 객체
        source_id: 소스 ID

    Returns:
        소스 정보
    """
    repo = get_source_repo(request)
    source = repo.get_by_id(source_id)

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    return source.model_dump(mode="json")


@router.post("", status_code=201)
async def create_source(
    request: Request,
    body: SourceCreateRequest,
) -> dict[str, Any]:
    """새 소스 생성.

    Args:
        request: FastAPI 요청 객체
        body: 소스 생성 요청

    Returns:
        생성된 소스 정보
    """
    repo = get_source_repo(request)
    now = datetime.now(UTC)

    source = Source(
        id=f"src_{uuid4().hex[:8]}",
        name=body.name,
        type=body.type,
        url=body.url,
        category=body.category,
        language=body.language,
        config=body.config,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    repo.create(source)

    logger.info("source_created", source_id=source.id, name=source.name)

    return source.model_dump(mode="json")


@router.put("/{source_id}")
async def update_source(
    request: Request,
    source_id: str,
    body: SourceUpdateRequest,
) -> dict[str, Any]:
    """소스 수정.

    Args:
        request: FastAPI 요청 객체
        source_id: 소스 ID
        body: 소스 수정 요청

    Returns:
        수정된 소스 정보
    """
    repo = get_source_repo(request)
    source = repo.get_by_id(source_id)

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # 업데이트할 필드만 적용
    update_data = body.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.now(UTC)

    for key, value in update_data.items():
        setattr(source, key, value)

    repo.update(source)

    logger.info("source_updated", source_id=source_id)

    return source.model_dump(mode="json")


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    request: Request,
    source_id: str,
) -> None:
    """소스 삭제.

    Args:
        request: FastAPI 요청 객체
        source_id: 소스 ID
    """
    repo = get_source_repo(request)
    source = repo.get_by_id(source_id)

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    repo.delete(source_id)

    logger.info("source_deleted", source_id=source_id)


@router.post("/{source_id}/activate")
async def activate_source(
    request: Request,
    source_id: str,
) -> dict[str, Any]:
    """소스 활성화.

    Args:
        request: FastAPI 요청 객체
        source_id: 소스 ID

    Returns:
        활성화된 소스 정보
    """
    repo = get_source_repo(request)
    source = repo.get_by_id(source_id)

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    now = datetime.now(UTC)
    source.is_active = True
    source.updated_at = now

    repo.update(source)

    logger.info("source_activated", source_id=source_id)

    return source.model_dump(mode="json")


@router.post("/{source_id}/deactivate")
async def deactivate_source(
    request: Request,
    source_id: str,
) -> dict[str, Any]:
    """소스 비활성화.

    Args:
        request: FastAPI 요청 객체
        source_id: 소스 ID

    Returns:
        비활성화된 소스 정보
    """
    repo = get_source_repo(request)
    source = repo.get_by_id(source_id)

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    repo.deactivate(source_id)
    source.is_active = False
    source.updated_at = datetime.now(UTC)

    logger.info("source_deactivated", source_id=source_id)

    return source.model_dump(mode="json")
