"""Content pipeline for collection and processing orchestration.

수집 → 번역 → 요약 → 스코어링 전체 파이프라인을 관리합니다.
"""

from typing import TYPE_CHECKING

import structlog

from src.adapters.gemini_client import GeminiClient
from src.agent.domains.processor.tools.scorer_tool import score_relevance
from src.agent.domains.processor.tools.summarizer_tool import summarize_content
from src.agent.domains.processor.tools.translator_tool import translate_content
from src.models.content import Content
from src.models.source import Source, SourceType
from src.repositories.content_repo import ContentRepository
from src.repositories.source_repo import SourceRepository

if TYPE_CHECKING:
    from src.adapters.tasks_client import TasksClient

logger = structlog.get_logger(__name__)


class ContentPipeline:
    """콘텐츠 수집 및 처리 파이프라인.

    활성 소스에서 콘텐츠를 수집하고 처리하는 전체 파이프라인을 관리합니다.
    """

    def __init__(
        self,
        source_repo: SourceRepository,
        content_repo: ContentRepository,
        gemini_client: GeminiClient,
        tasks_client: "TasksClient | None" = None,
    ) -> None:
        """ContentPipeline 초기화.

        Args:
            source_repo: 소스 리포지토리
            content_repo: 콘텐츠 리포지토리
            gemini_client: Gemini 클라이언트
            tasks_client: Cloud Tasks 클라이언트 (수집 후 처리 작업 enqueue용)
        """
        self.source_repo = source_repo
        self.content_repo = content_repo
        self.gemini_client = gemini_client
        self.tasks_client = tasks_client

        # TasksClient가 있으면 process 핸들러 등록 (direct 모드용)
        if tasks_client:
            tasks_client.register_handler("process", self._handle_process_task)

    def collect_from_sources(self) -> dict[str, int]:
        """활성 소스에서 콘텐츠 수집.

        수집 후 각 콘텐츠에 대해 Cloud Tasks로 처리 작업을 enqueue합니다.
        TASKS_MODE=direct일 경우 즉시 처리됩니다.

        Returns:
            수집 결과 통계 (total_sources, collected, enqueued, errors)
        """
        sources = self.source_repo.find_active_sources()

        result: dict[str, int] = {
            "total_sources": len(sources),
            "collected": 0,
            "enqueued": 0,
            "errors": 0,
        }

        for source in sources:
            try:
                content_ids = self._collect_from_source(source)
                result["collected"] += len(content_ids)

                # 수집된 콘텐츠에 대해 처리 작업 enqueue
                if self.tasks_client:
                    for content_id in content_ids:
                        try:
                            self.tasks_client.enqueue(
                                "process",
                                {"content_id": content_id},
                            )
                            result["enqueued"] += 1
                        except Exception as e:
                            logger.error(
                                "enqueue_failed",
                                content_id=content_id,
                                error=str(e),
                            )

            except Exception as e:
                logger.error(
                    "source_collection_failed",
                    source_id=source.id,
                    error=str(e),
                )
                result["errors"] += 1
                self.source_repo.increment_error_count(source.id)

        return result

    def _collect_from_source(self, source: Source) -> list[str]:
        """단일 소스에서 콘텐츠 수집.

        Args:
            source: 수집할 소스

        Returns:
            수집된 콘텐츠 ID 목록
        """
        if source.type == SourceType.RSS:
            return self._collect_from_rss(source)
        elif source.type == SourceType.YOUTUBE:
            return self._collect_from_youtube(source)
        else:
            logger.warning(
                "unsupported_source_type",
                source_id=source.id,
                source_type=source.type,
            )
            return []

    def _collect_from_rss(self, source: Source) -> list[str]:
        """RSS 소스에서 수집.

        Args:
            source: RSS 소스

        Returns:
            수집된 콘텐츠 ID 목록
        """
        # 실제 구현은 rss_tool.fetch_rss 호출
        from src.agent.domains.collector.tools.rss_tool import fetch_rss

        contents = fetch_rss(
            source_id=source.id,
            source_url=str(source.url),
            content_repo=self.content_repo,
        )
        return [c.id for c in contents]

    def _collect_from_youtube(self, source: Source) -> list[str]:
        """YouTube 소스에서 수집.

        Args:
            source: YouTube 소스

        Returns:
            수집된 콘텐츠 ID 목록
        """
        # YouTube 수집 로직
        # 여기서는 인터페이스만 정의
        return []

    def _handle_process_task(self, payload: dict[str, str]) -> None:
        """Cloud Tasks process 핸들러 (direct 모드용).

        Args:
            payload: {"content_id": "..."}

        Raises:
            ValueError: 콘텐츠를 찾을 수 없는 경우
        """
        content_id = payload.get("content_id")
        if not content_id:
            raise ValueError("content_id is required")

        content = self.content_repo.get_by_id(content_id)
        if not content:
            raise ValueError(f"Content not found: {content_id}")

        success = self._process_single_content(content)
        if not success:
            raise ValueError(f"Processing failed for: {content_id}")

    def _process_single_content(self, content: Content) -> bool:
        """단일 콘텐츠 처리 (번역 → 요약 → 스코어링).

        Args:
            content: 처리할 콘텐츠

        Returns:
            처리 성공 여부
        """
        try:
            # 1. 번역
            translation = translate_content(
                content=content,
                gemini_client=self.gemini_client,
                target_lang="ko",
            )

            # 2. 요약
            summary = summarize_content(
                content=content,
                title_ko=translation.title_ko,
                body_ko=translation.body_ko,
                gemini_client=self.gemini_client,
            )

            # 3. 스코어링
            scoring = score_relevance(
                content=content,
                summary_ko=summary.summary_ko,
                why_important=summary.why_important,
                gemini_client=self.gemini_client,
                categories=summary.categories,
            )

            # 4. 결과 저장
            self.content_repo.update_processing_result(
                content_id=content.id,
                title_ko=summary.title_ko,
                summary_ko=summary.summary_ko,
                why_important=summary.why_important,
                relevance_score=scoring.score,
                categories=summary.categories,
            )

            logger.info(
                "content_processed",
                content_id=content.id,
                relevance_score=scoring.score,
            )
            return True

        except Exception as e:
            logger.error(
                "content_processing_failed",
                content_id=content.id,
                error=str(e),
            )
            self.content_repo.increment_processing_attempts(content.id, str(e))
            return False
