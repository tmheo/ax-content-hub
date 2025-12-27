"""Repository for Source entities.

Firestore sources 컬렉션에 대한 데이터 접근 레이어.
"""

from datetime import UTC, datetime

from src.adapters.firestore_client import FirestoreClient
from src.models.source import Source, SourceType
from src.repositories.base import BaseRepository


class SourceRepository(BaseRepository[Source]):
    """Source 엔티티 Repository.

    Firestore Collection: sources
    """

    collection_name = "sources"
    model_class = Source

    def __init__(self, firestore_client: FirestoreClient) -> None:
        """Initialize SourceRepository.

        Args:
            firestore_client: Firestore 클라이언트 인스턴스.
        """
        super().__init__(firestore_client)

    def find_active_sources(self) -> list[Source]:
        """활성화된 모든 소스 조회.

        Returns:
            활성 소스 목록.
        """
        return self.find_by([("is_active", "==", True)])

    def find_by_type(self, source_type: SourceType) -> list[Source]:
        """타입별 소스 조회.

        Args:
            source_type: 소스 타입 (rss/youtube).

        Returns:
            해당 타입의 소스 목록.
        """
        return self.find_by([("type", "==", source_type.value)])

    def find_active_by_type(self, source_type: SourceType) -> list[Source]:
        """타입별 활성 소스 조회.

        Args:
            source_type: 소스 타입 (rss/youtube).

        Returns:
            해당 타입의 활성 소스 목록.
        """
        return self.find_by(
            [
                ("is_active", "==", True),
                ("type", "==", source_type.value),
            ]
        )

    def update_last_fetched(self, source_id: str, fetched_at: datetime) -> None:
        """마지막 수집 시간 업데이트.

        Args:
            source_id: 소스 ID.
            fetched_at: 수집 시간.
        """
        self._db.update(
            self.collection_name,
            source_id,
            {
                "last_fetched_at": fetched_at,
                "updated_at": datetime.now(UTC),
            },
        )

    def increment_error_count(self, source_id: str) -> None:
        """에러 카운트 증가.

        연속 실패 횟수가 3회 이상이면 자동으로 비활성화합니다.

        Args:
            source_id: 소스 ID.
        """
        source = self.get_by_id(source_id)
        if source is None:
            return

        new_count = source.fetch_error_count + 1
        update_data: dict[str, object] = {
            "fetch_error_count": new_count,
            "updated_at": datetime.now(UTC),
        }

        # 연속 실패 3회 이상 시 자동 비활성화
        if new_count >= 3:
            update_data["is_active"] = False

        self._db.update(
            self.collection_name,
            source_id,
            update_data,
        )

    def reset_error_count(self, source_id: str) -> None:
        """에러 카운트 리셋.

        Args:
            source_id: 소스 ID.
        """
        self._db.update(
            self.collection_name,
            source_id,
            {
                "fetch_error_count": 0,
                "updated_at": datetime.now(UTC),
            },
        )

    def deactivate(self, source_id: str) -> None:
        """소스 비활성화.

        Args:
            source_id: 소스 ID.
        """
        self._db.update(
            self.collection_name,
            source_id,
            {
                "is_active": False,
                "updated_at": datetime.now(UTC),
            },
        )
