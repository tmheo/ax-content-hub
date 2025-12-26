"""Tests for subscriptions CRUD API endpoints."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.models.subscription import (
    DeliveryFrequency,
    Subscription,
    SubscriptionPreferences,
)


class TestSubscriptionsEndpoints:
    """Tests for subscriptions API endpoints."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """테스트용 FastAPI 앱."""
        from src.api.subscriptions import router

        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """테스트 클라이언트."""
        return TestClient(app)

    @pytest.fixture
    def sample_subscription(self) -> Subscription:
        """샘플 구독."""
        now = datetime.now(UTC)
        return Subscription(
            id="sub_001",
            platform="slack",
            platform_config={
                "team_id": "T12345",
                "channel_id": "C12345678",
            },
            preferences=SubscriptionPreferences(
                frequency=DeliveryFrequency.DAILY,
                delivery_time="09:00",
                min_relevance=0.3,
                categories=["AI", "Technology"],
            ),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    def test_list_subscriptions(
        self,
        client: TestClient,
        sample_subscription: Subscription,
    ) -> None:
        """GET /subscriptions 구독 목록 조회."""
        with patch("src.api.subscriptions.get_subscription_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.find_all.return_value = [sample_subscription]
            mock_get.return_value = mock_repo

            response = client.get("/subscriptions")

        assert response.status_code == 200
        data = response.json()
        assert len(data["subscriptions"]) == 1
        assert data["subscriptions"][0]["id"] == "sub_001"

    def test_list_subscriptions_active_only(
        self,
        client: TestClient,
        sample_subscription: Subscription,
    ) -> None:
        """GET /subscriptions?active=true 활성 구독만 조회."""
        with patch("src.api.subscriptions.get_subscription_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.find_active_subscriptions.return_value = [sample_subscription]
            mock_get.return_value = mock_repo

            response = client.get("/subscriptions?active=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["subscriptions"]) == 1

    def test_get_subscription(
        self,
        client: TestClient,
        sample_subscription: Subscription,
    ) -> None:
        """GET /subscriptions/{subscription_id} 단일 구독 조회."""
        with patch("src.api.subscriptions.get_subscription_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = sample_subscription
            mock_get.return_value = mock_repo

            response = client.get("/subscriptions/sub_001")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "sub_001"
        assert data["platform"] == "slack"
        assert data["platform_config"]["channel_id"] == "C12345678"

    def test_get_subscription_not_found(
        self,
        client: TestClient,
    ) -> None:
        """GET /subscriptions/{subscription_id} 존재하지 않는 구독."""
        with patch("src.api.subscriptions.get_subscription_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = None
            mock_get.return_value = mock_repo

            response = client.get("/subscriptions/sub_999")

        assert response.status_code == 404

    def test_create_subscription(
        self,
        client: TestClient,
    ) -> None:
        """POST /subscriptions 새 구독 생성."""
        with patch("src.api.subscriptions.get_subscription_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.create.return_value = None
            mock_get.return_value = mock_repo

            response = client.post(
                "/subscriptions",
                json={
                    "platform_config": {
                        "team_id": "T12345",
                        "channel_id": "C12345678",
                    },
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "slack"
        assert data["platform_config"]["channel_id"] == "C12345678"
        mock_repo.create.assert_called_once()

    def test_create_subscription_with_preferences(
        self,
        client: TestClient,
    ) -> None:
        """POST /subscriptions 선호도 설정 포함 구독 생성."""
        with patch("src.api.subscriptions.get_subscription_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.create.return_value = None
            mock_get.return_value = mock_repo

            response = client.post(
                "/subscriptions",
                json={
                    "platform_config": {
                        "team_id": "T12345",
                        "channel_id": "C12345678",
                    },
                    "preferences": {
                        "frequency": "daily",
                        "delivery_time": "10:00",
                        "min_relevance": 0.5,
                        "categories": ["AI"],
                    },
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["preferences"]["min_relevance"] == 0.5
        assert data["preferences"]["delivery_time"] == "10:00"

    def test_update_subscription(
        self,
        client: TestClient,
        sample_subscription: Subscription,
    ) -> None:
        """PUT /subscriptions/{subscription_id} 구독 수정."""
        with patch("src.api.subscriptions.get_subscription_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = sample_subscription
            mock_repo.update.return_value = None
            mock_get.return_value = mock_repo

            response = client.put(
                "/subscriptions/sub_001",
                json={
                    "preferences": {
                        "delivery_time": "10:00",
                    },
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["preferences"]["delivery_time"] == "10:00"

    def test_update_subscription_not_found(
        self,
        client: TestClient,
    ) -> None:
        """PUT /subscriptions/{subscription_id} 존재하지 않는 구독 수정."""
        with patch("src.api.subscriptions.get_subscription_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = None
            mock_get.return_value = mock_repo

            response = client.put(
                "/subscriptions/sub_999",
                json={"preferences": {"delivery_time": "10:00"}},
            )

        assert response.status_code == 404

    def test_delete_subscription(
        self,
        client: TestClient,
        sample_subscription: Subscription,
    ) -> None:
        """DELETE /subscriptions/{subscription_id} 구독 삭제."""
        with patch("src.api.subscriptions.get_subscription_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = sample_subscription
            mock_repo.delete.return_value = None
            mock_get.return_value = mock_repo

            response = client.delete("/subscriptions/sub_001")

        assert response.status_code == 204
        mock_repo.delete.assert_called_once_with("sub_001")

    def test_delete_subscription_not_found(
        self,
        client: TestClient,
    ) -> None:
        """DELETE /subscriptions/{subscription_id} 존재하지 않는 구독 삭제."""
        with patch("src.api.subscriptions.get_subscription_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = None
            mock_get.return_value = mock_repo

            response = client.delete("/subscriptions/sub_999")

        assert response.status_code == 404

    def test_activate_subscription(
        self,
        client: TestClient,
        sample_subscription: Subscription,
    ) -> None:
        """POST /subscriptions/{subscription_id}/activate 구독 활성화."""
        inactive_sub = sample_subscription.model_copy()
        inactive_sub.is_active = False

        with patch("src.api.subscriptions.get_subscription_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = inactive_sub
            mock_repo.activate_subscription.return_value = None
            mock_get.return_value = mock_repo

            response = client.post("/subscriptions/sub_001/activate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    def test_deactivate_subscription(
        self,
        client: TestClient,
        sample_subscription: Subscription,
    ) -> None:
        """POST /subscriptions/{subscription_id}/deactivate 구독 비활성화."""
        with patch("src.api.subscriptions.get_subscription_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = sample_subscription
            mock_repo.deactivate_subscription.return_value = None
            mock_get.return_value = mock_repo

            response = client.post("/subscriptions/sub_001/deactivate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
