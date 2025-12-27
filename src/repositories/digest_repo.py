"""Repository for Digest entities.

Firestore digests 컬렉션에 대한 데이터 접근 레이어.
"""

from datetime import UTC, datetime

from src.adapters.firestore_client import FirestoreClient
from src.models.digest import Digest, DigestStatus
from src.repositories.base import BaseRepository


class DigestRepository(BaseRepository[Digest]):
    """Digest 엔티티 Repository.

    Firestore Collection: digests
    """

    collection_name = "digests"
    model_class = Digest

    def __init__(self, firestore_client: FirestoreClient) -> None:
        """Initialize DigestRepository.

        Args:
            firestore_client: Firestore 클라이언트 인스턴스.
        """
        super().__init__(firestore_client)

    def get_by_digest_key(self, digest_key: str) -> Digest | None:
        """digest_key로 다이제스트 조회.

        Args:
            digest_key: 멱등성 키.

        Returns:
            다이제스트 또는 None.
        """
        results = self.find_by([("digest_key", "==", digest_key)])
        return results[0] if results else None

    def exists_by_digest_key(self, digest_key: str) -> bool:
        """digest_key 존재 여부 확인.

        Args:
            digest_key: 멱등성 키.

        Returns:
            존재하면 True.
        """
        return self.get_by_digest_key(digest_key) is not None

    def find_by_subscription(self, subscription_id: str) -> list[Digest]:
        """구독별 다이제스트 조회.

        Args:
            subscription_id: 구독 ID.

        Returns:
            해당 구독의 다이제스트 목록.
        """
        return self.find_by([("subscription_id", "==", subscription_id)])

    def find_by_status(self, status: DigestStatus) -> list[Digest]:
        """상태별 다이제스트 조회.

        Args:
            status: 다이제스트 상태.

        Returns:
            해당 상태의 다이제스트 목록.
        """
        return self.find_by([("status", "==", status.value)])

    def find_pending_for_sending(self, limit: int = 50) -> list[Digest]:
        """발송 대기 중인 다이제스트 조회.

        Args:
            limit: 최대 조회 수.

        Returns:
            발송 대기 다이제스트 목록.
        """
        results = self.find_by([("status", "==", DigestStatus.PENDING.value)])
        return results[:limit]

    def update_status(self, digest_id: str, status: DigestStatus) -> None:
        """상태 업데이트.

        Args:
            digest_id: 다이제스트 ID.
            status: 새 상태.
        """
        self._db.update(
            self.collection_name,
            digest_id,
            {"status": status.value},
        )

    def update_sent_info(
        self,
        digest_id: str,
        message_ts: str,
    ) -> None:
        """발송 정보 업데이트.

        Args:
            digest_id: 다이제스트 ID.
            message_ts: Slack 메시지 타임스탬프.
        """
        self._db.update(
            self.collection_name,
            digest_id,
            {
                "slack_message_ts": message_ts,
                "status": DigestStatus.SENT.value,
                "sent_at": datetime.now(UTC),
            },
        )

    def mark_as_failed(self, digest_id: str, error: str) -> None:
        """실패 상태로 마킹.

        Args:
            digest_id: 다이제스트 ID.
            error: 에러 메시지.
        """
        self._db.update(
            self.collection_name,
            digest_id,
            {
                "status": DigestStatus.FAILED.value,
                "error": error,
            },
        )
