"""Repository for Subscription entities.

Firestore subscriptions 컬렉션에 대한 데이터 접근 레이어.
"""

from datetime import UTC, datetime

from src.adapters.firestore_client import FirestoreClient
from src.models.subscription import DeliveryFrequency, Subscription
from src.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    """Subscription 엔티티 Repository.

    Firestore Collection: subscriptions
    """

    collection_name = "subscriptions"
    model_class = Subscription

    def __init__(self, firestore_client: FirestoreClient) -> None:
        """Initialize SubscriptionRepository.

        Args:
            firestore_client: Firestore 클라이언트 인스턴스.
        """
        super().__init__(firestore_client)

    def find_active_subscriptions(self) -> list[Subscription]:
        """활성 구독 조회.

        Returns:
            활성 구독 목록.
        """
        return self.find_by([("is_active", "==", True)])

    def find_by_channel(self, channel_id: str) -> Subscription | None:
        """채널별 구독 조회.

        Args:
            channel_id: 슬랙 채널 ID.

        Returns:
            구독 또는 None.
        """
        results = self.find_by([("platform_config.channel_id", "==", channel_id)])
        return results[0] if results else None

    def find_by_frequency(self, frequency: DeliveryFrequency) -> list[Subscription]:
        """빈도별 구독 조회.

        Args:
            frequency: 배송 빈도.

        Returns:
            해당 빈도의 구독 목록.
        """
        return self.find_by([("preferences.frequency", "==", frequency.value)])

    def find_due_for_delivery(self, delivery_time: str) -> list[Subscription]:
        """배송 예정 구독 조회.

        특정 시간에 배송해야 하는 활성 구독을 조회합니다.

        Args:
            delivery_time: 배송 시간 (HH:MM 형식).

        Returns:
            배송 예정 구독 목록.
        """
        return self.find_by(
            [
                ("is_active", "==", True),
                ("preferences.delivery_time", "==", delivery_time),
            ]
        )

    def update_last_delivered(self, subscription_id: str) -> None:
        """마지막 배송 시간 업데이트.

        Args:
            subscription_id: 구독 ID.
        """
        self._db.update(
            self.collection_name,
            subscription_id,
            {"last_delivered_at": datetime.now(UTC)},
        )

    def update_source_ids(
        self,
        subscription_id: str,
        source_ids: list[str],
    ) -> None:
        """소스 ID 목록 업데이트.

        Args:
            subscription_id: 구독 ID.
            source_ids: 새 소스 ID 목록.
        """
        self._db.update(
            self.collection_name,
            subscription_id,
            {"source_ids": source_ids},
        )

    def deactivate(self, subscription_id: str) -> None:
        """구독 비활성화.

        Args:
            subscription_id: 구독 ID.
        """
        self._db.update(
            self.collection_name,
            subscription_id,
            {"is_active": False},
        )

    def activate(self, subscription_id: str) -> None:
        """구독 활성화.

        Args:
            subscription_id: 구독 ID.
        """
        self._db.update(
            self.collection_name,
            subscription_id,
            {"is_active": True},
        )
