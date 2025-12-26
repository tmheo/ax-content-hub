"""Repository for Content entities.

Firestore contents 컬렉션에 대한 데이터 접근 레이어.
"""

from datetime import UTC, datetime
from typing import Any

from src.adapters.firestore_client import FirestoreClient
from src.models.content import Content, ProcessingStatus
from src.repositories.base import BaseRepository


class ContentRepository(BaseRepository[Content]):
    """Content 엔티티 Repository.

    Firestore Collection: contents
    """

    collection_name = "contents"
    model_class = Content

    def __init__(self, firestore_client: FirestoreClient) -> None:
        """Initialize ContentRepository.

        Args:
            firestore_client: Firestore 클라이언트 인스턴스.
        """
        super().__init__(firestore_client)

    def get_by_content_key(self, content_key: str) -> Content | None:
        """content_key로 콘텐츠 조회.

        Args:
            content_key: 멱등성 키.

        Returns:
            콘텐츠 또는 None.
        """
        results = self.find_by([("content_key", "==", content_key)])
        return results[0] if results else None

    def exists_by_content_key(self, content_key: str) -> bool:
        """content_key 존재 여부 확인.

        Args:
            content_key: 멱등성 키.

        Returns:
            존재하면 True.
        """
        return self.get_by_content_key(content_key) is not None

    def find_by_status(self, status: ProcessingStatus) -> list[Content]:
        """상태별 콘텐츠 조회.

        Args:
            status: 처리 상태.

        Returns:
            해당 상태의 콘텐츠 목록.
        """
        return self.find_by([("processing_status", "==", status.value)])

    def find_by_source(self, source_id: str) -> list[Content]:
        """소스별 콘텐츠 조회.

        Args:
            source_id: 소스 ID.

        Returns:
            해당 소스의 콘텐츠 목록.
        """
        return self.find_by([("source_id", "==", source_id)])

    def find_pending_for_processing(self, limit: int = 100) -> list[Content]:
        """처리 대기 중인 콘텐츠 조회.

        Args:
            limit: 최대 조회 수.

        Returns:
            처리 대기 콘텐츠 목록.
        """
        # Firestore 쿼리로 pending 상태만 조회
        results = self.find_by(
            [("processing_status", "==", ProcessingStatus.PENDING.value)]
        )
        return results[:limit]

    def find_for_digest(
        self,
        min_relevance: float = 0.3,
        limit: int = 20,
    ) -> list[Content]:
        """다이제스트용 콘텐츠 조회.

        완료된 콘텐츠 중 최소 관련성 점수 이상이고,
        아직 다이제스트에 포함되지 않은 것들을 조회합니다.

        Args:
            min_relevance: 최소 관련성 점수.
            limit: 최대 조회 수.

        Returns:
            다이제스트용 콘텐츠 목록.
        """
        # Firestore에서 완료 상태만 조회
        results = self.find_by(
            [("processing_status", "==", ProcessingStatus.COMPLETED.value)]
        )

        # 애플리케이션 레벨에서 필터링:
        # 1. 관련성 점수 충족
        # 2. 아직 다이제스트에 포함되지 않음
        filtered = [
            c
            for c in results
            if c.relevance_score is not None
            and c.relevance_score >= min_relevance
            and c.included_in_digest_id is None
        ]

        # 관련성 점수로 정렬
        filtered.sort(key=lambda x: x.relevance_score or 0, reverse=True)

        return filtered[:limit]

    def find_by_ids(self, content_ids: list[str]) -> list[Content]:
        """여러 ID로 콘텐츠 조회.

        Args:
            content_ids: 콘텐츠 ID 목록.

        Returns:
            콘텐츠 목록 (순서는 보장되지 않음).
        """
        if not content_ids:
            return []

        # 개별 조회 후 필터링
        results = []
        for content_id in content_ids:
            content = self.get_by_id(content_id)
            if content:
                results.append(content)
        return results

    def update_processing_status(
        self,
        content_id: str,
        status: ProcessingStatus,
    ) -> None:
        """처리 상태 업데이트.

        Args:
            content_id: 콘텐츠 ID.
            status: 새 상태.
        """
        self._db.update(
            self.collection_name,
            content_id,
            {"processing_status": status.value},
        )

    def update_processing_result(
        self,
        content_id: str,
        title_ko: str,
        summary_ko: str,
        why_important: str,
        relevance_score: float,
        categories: list[str] | None = None,
    ) -> None:
        """처리 결과 업데이트.

        Args:
            content_id: 콘텐츠 ID.
            title_ko: 한국어 제목.
            summary_ko: 한국어 요약.
            why_important: 중요성 설명.
            relevance_score: 관련성 점수.
            categories: 카테고리 목록.
        """
        self._db.update(
            self.collection_name,
            content_id,
            {
                "title_ko": title_ko,
                "summary_ko": summary_ko,
                "why_important": why_important,
                "relevance_score": relevance_score,
                "categories": categories or [],
                "processing_status": ProcessingStatus.COMPLETED.value,
                "processed_at": datetime.now(UTC),
            },
        )

    def increment_processing_attempts(
        self,
        content_id: str,
        error: str | None = None,
    ) -> None:
        """처리 시도 횟수 증가.

        Args:
            content_id: 콘텐츠 ID.
            error: 에러 메시지.
        """
        content = self.get_by_id(content_id)
        if content is None:
            return

        new_count = content.processing_attempts + 1
        update_data: dict[str, Any] = {
            "processing_attempts": new_count,
        }
        if error:
            update_data["last_error"] = error

        self._db.update(self.collection_name, content_id, update_data)

    def mark_as_failed(self, content_id: str, error: str) -> None:
        """실패 상태로 마킹.

        Args:
            content_id: 콘텐츠 ID.
            error: 에러 메시지.
        """
        self._db.update(
            self.collection_name,
            content_id,
            {
                "processing_status": ProcessingStatus.FAILED.value,
                "last_error": error,
            },
        )

    def mark_as_skipped(self, content_id: str, reason: str) -> None:
        """건너뜀 상태로 마킹.

        Args:
            content_id: 콘텐츠 ID.
            reason: 건너뛴 이유.
        """
        self._db.update(
            self.collection_name,
            content_id,
            {
                "processing_status": ProcessingStatus.SKIPPED.value,
                "last_error": reason,
            },
        )

    def mark_as_included_in_digest(
        self, content_ids: list[str], digest_id: str
    ) -> None:
        """다이제스트에 포함됨으로 마킹.

        Args:
            content_ids: 콘텐츠 ID 목록.
            digest_id: 다이제스트 ID.
        """
        for content_id in content_ids:
            self._db.update(
                self.collection_name,
                content_id,
                {"included_in_digest_id": digest_id},
            )
