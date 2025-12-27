"""Tests for SubscriptionRepository."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.models.subscription import DeliveryFrequency
from src.repositories.subscription_repo import SubscriptionRepository


class TestSubscriptionRepository:
    """Tests for SubscriptionRepository."""

    @pytest.fixture
    def mock_firestore_client(self) -> MagicMock:
        """Mock FirestoreClient."""
        return MagicMock()

    @pytest.fixture
    def subscription_repo(
        self, mock_firestore_client: MagicMock
    ) -> SubscriptionRepository:
        """SubscriptionRepository 인스턴스."""
        return SubscriptionRepository(mock_firestore_client)

    @pytest.fixture
    def sample_subscription_data(self) -> dict:
        """샘플 구독 데이터."""
        now = datetime.now(UTC)
        return {
            "id": "sub_001",
            "platform": "slack",
            "platform_config": {
                "team_id": "T123456",
                "channel_id": "C123456789",
            },
            "preferences": {
                "frequency": "daily",
                "delivery_time": "09:00",
                "categories": [],
                "min_relevance": 0.3,
                "language": "ko",
            },
            "is_active": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

    def test_collection_name(self, subscription_repo: SubscriptionRepository) -> None:
        """컬렉션 이름 확인."""
        assert subscription_repo.collection_name == "subscriptions"

    def test_get_by_id(
        self,
        subscription_repo: SubscriptionRepository,
        mock_firestore_client: MagicMock,
        sample_subscription_data: dict,
    ) -> None:
        """ID로 조회."""
        mock_firestore_client.get.return_value = sample_subscription_data

        result = subscription_repo.get_by_id("sub_001")

        assert result is not None
        assert result.id == "sub_001"

    def test_find_active_subscriptions(
        self,
        subscription_repo: SubscriptionRepository,
        mock_firestore_client: MagicMock,
        sample_subscription_data: dict,
    ) -> None:
        """활성 구독 조회."""
        mock_firestore_client.query.return_value = [sample_subscription_data]

        results = subscription_repo.find_active_subscriptions()

        assert len(results) == 1
        assert results[0].is_active is True

    def test_find_by_channel(
        self,
        subscription_repo: SubscriptionRepository,
        mock_firestore_client: MagicMock,
        sample_subscription_data: dict,
    ) -> None:
        """채널별 구독 조회."""
        mock_firestore_client.query.return_value = [sample_subscription_data]

        result = subscription_repo.find_by_channel("C123456789")

        assert result is not None
        assert result.platform_config["channel_id"] == "C123456789"

    def test_find_by_channel_not_found(
        self,
        subscription_repo: SubscriptionRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """채널 없는 경우."""
        mock_firestore_client.query.return_value = []

        result = subscription_repo.find_by_channel("C999999")

        assert result is None

    def test_find_by_frequency(
        self,
        subscription_repo: SubscriptionRepository,
        mock_firestore_client: MagicMock,
        sample_subscription_data: dict,
    ) -> None:
        """빈도별 구독 조회."""
        mock_firestore_client.query.return_value = [sample_subscription_data]

        results = subscription_repo.find_by_frequency(DeliveryFrequency.DAILY)

        assert len(results) == 1

    def test_find_due_for_delivery(
        self,
        subscription_repo: SubscriptionRepository,
        mock_firestore_client: MagicMock,
        sample_subscription_data: dict,
    ) -> None:
        """배송 예정 구독 조회."""
        mock_firestore_client.query.return_value = [sample_subscription_data]

        results = subscription_repo.find_due_for_delivery("09:00")

        assert len(results) == 1

    def test_update_last_delivered(
        self,
        subscription_repo: SubscriptionRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """마지막 배송 시간 업데이트."""
        subscription_repo.update_last_delivered("sub_001")

        mock_firestore_client.update.assert_called_once()
        call_args = mock_firestore_client.update.call_args
        assert call_args[0][0] == "subscriptions"
        assert call_args[0][1] == "sub_001"
        assert "last_delivered_at" in call_args[0][2]

    def test_update_source_ids(
        self,
        subscription_repo: SubscriptionRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """소스 ID 목록 업데이트."""
        new_sources = ["src_001", "src_002", "src_003"]

        subscription_repo.update_source_ids("sub_001", new_sources)

        mock_firestore_client.update.assert_called_once()
        call_args = mock_firestore_client.update.call_args
        assert call_args[0][2]["source_ids"] == new_sources

    def test_deactivate_subscription(
        self,
        subscription_repo: SubscriptionRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """구독 비활성화."""
        subscription_repo.deactivate("sub_001")

        mock_firestore_client.update.assert_called_once()
        call_args = mock_firestore_client.update.call_args
        assert call_args[0][2]["is_active"] is False

    def test_activate_subscription(
        self,
        subscription_repo: SubscriptionRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """구독 활성화."""
        subscription_repo.activate("sub_001")

        mock_firestore_client.update.assert_called_once()
        call_args = mock_firestore_client.update.call_args
        assert call_args[0][2]["is_active"] is True
