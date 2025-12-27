"""Tests for scheduler endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestSchedulerEndpoints:
    """Tests for scheduler API endpoints."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """테스트용 FastAPI 앱."""
        from src.api.scheduler import router

        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """테스트 클라이언트."""
        return TestClient(app)

    def test_collect_endpoint(self, client: TestClient) -> None:
        """POST /internal/collect 콘텐츠 수집 및 처리 enqueue."""
        with patch("src.api.scheduler.get_content_pipeline") as mock_get:
            mock_pipeline = MagicMock()
            mock_pipeline.collect_from_sources.return_value = {
                "total_sources": 5,
                "collected": 10,
                "enqueued": 10,
                "errors": 0,
            }
            mock_get.return_value = mock_pipeline

            response = client.post("/internal/collect")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["result"]["total_sources"] == 5
        assert data["result"]["enqueued"] == 10

    def test_distribute_endpoint(self, client: TestClient) -> None:
        """POST /internal/distribute 다이제스트 생성 및 발송."""
        with patch("src.api.scheduler.get_digest_service") as mock_get:
            mock_service = MagicMock()

            # Mock subscription_repo
            mock_subscription = MagicMock()
            mock_subscription.id = "sub_001"
            mock_subscription.preferences.min_relevance = 0.3
            mock_service.subscription_repo.find_active_subscriptions.return_value = [
                mock_subscription
            ]

            # Mock digest creation
            mock_digest = MagicMock()
            mock_digest.status.value = "pending"
            mock_service.create_digest.return_value = mock_digest

            # Mock digest sending
            mock_service.send_digest.return_value = True

            mock_get.return_value = mock_service

            response = client.post("/internal/distribute")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["result"]["total_subscriptions"] == 1
        assert data["result"]["sent"] == 1

    def test_collect_with_error(self, client: TestClient) -> None:
        """수집 중 에러 발생 시 처리."""
        with patch("src.api.scheduler.get_content_pipeline") as mock_get:
            mock_pipeline = MagicMock()
            mock_pipeline.collect_from_sources.side_effect = Exception("Database error")
            mock_get.return_value = mock_pipeline

            response = client.post("/internal/collect")

        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["status"] == "error"
        assert "Database error" in data["detail"]["error"]
