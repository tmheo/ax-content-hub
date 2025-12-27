"""Tests for internal tasks endpoints (Cloud Tasks callbacks)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestInternalTasksEndpoints:
    """Tests for internal tasks API endpoints."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """테스트용 FastAPI 앱."""
        from src.api.internal_tasks import router

        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """테스트 클라이언트."""
        return TestClient(app)

    def test_process_content_task(self, client: TestClient) -> None:
        """POST /internal/tasks/process 단일 콘텐츠 처리."""
        with patch("src.api.internal_tasks.get_content_pipeline") as mock_get:
            mock_pipeline = MagicMock()
            mock_pipeline._process_single_content.return_value = True
            mock_get.return_value = mock_pipeline

            with patch("src.api.internal_tasks.get_content_repo") as mock_repo_get:
                mock_repo = MagicMock()
                mock_content = MagicMock()
                mock_content.id = "cnt_001"
                mock_repo.get_by_id.return_value = mock_content
                mock_repo_get.return_value = mock_repo

                response = client.post(
                    "/internal/tasks/process",
                    json={"content_id": "cnt_001"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["content_id"] == "cnt_001"

    def test_process_content_task_not_found(self, client: TestClient) -> None:
        """존재하지 않는 콘텐츠 처리 요청."""
        with patch("src.api.internal_tasks.get_content_repo") as mock_repo_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_get.return_value = mock_repo

            response = client.post(
                "/internal/tasks/process",
                json={"content_id": "cnt_999"},
            )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_process_content_task_failure(self, client: TestClient) -> None:
        """콘텐츠 처리 실패 시 에러 응답."""
        with patch("src.api.internal_tasks.get_content_pipeline") as mock_get:
            mock_pipeline = MagicMock()
            mock_pipeline._process_single_content.return_value = False
            mock_get.return_value = mock_pipeline

            with patch("src.api.internal_tasks.get_content_repo") as mock_repo_get:
                mock_repo = MagicMock()
                mock_content = MagicMock()
                mock_content.id = "cnt_001"
                mock_repo.get_by_id.return_value = mock_content
                mock_repo_get.return_value = mock_repo

                response = client.post(
                    "/internal/tasks/process",
                    json={"content_id": "cnt_001"},
                )

        assert response.status_code == 500
        data = response.json()
        assert "failed" in data["detail"]["error"].lower()

    def test_send_digest_task(self, client: TestClient) -> None:
        """POST /internal/tasks/send-digest 단일 다이제스트 발송."""
        with patch("src.api.internal_tasks.get_digest_service") as mock_get:
            mock_service = MagicMock()
            mock_service.send_digest.return_value = True
            mock_get.return_value = mock_service

            with patch("src.api.internal_tasks.get_digest_repo") as mock_repo_get:
                mock_repo = MagicMock()
                mock_digest = MagicMock()
                mock_digest.id = "dgst_001"
                mock_repo.get_by_id.return_value = mock_digest
                mock_repo_get.return_value = mock_repo

                response = client.post(
                    "/internal/tasks/send-digest",
                    json={"digest_id": "dgst_001"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["digest_id"] == "dgst_001"

    def test_send_digest_task_not_found(self, client: TestClient) -> None:
        """존재하지 않는 다이제스트 발송 요청."""
        with patch("src.api.internal_tasks.get_digest_repo") as mock_repo_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_get.return_value = mock_repo

            response = client.post(
                "/internal/tasks/send-digest",
                json={"digest_id": "dgst_999"},
            )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_send_digest_task_failure(self, client: TestClient) -> None:
        """다이제스트 발송 실패 시 에러 응답."""
        with patch("src.api.internal_tasks.get_digest_service") as mock_get:
            mock_service = MagicMock()
            mock_service.send_digest.return_value = False
            mock_get.return_value = mock_service

            with patch("src.api.internal_tasks.get_digest_repo") as mock_repo_get:
                mock_repo = MagicMock()
                mock_digest = MagicMock()
                mock_digest.id = "dgst_001"
                mock_repo.get_by_id.return_value = mock_digest
                mock_repo_get.return_value = mock_repo

                response = client.post(
                    "/internal/tasks/send-digest",
                    json={"digest_id": "dgst_001"},
                )

        assert response.status_code == 500
        data = response.json()
        assert "failed" in data["detail"]["error"].lower()

    def test_collect_source_task(self, client: TestClient) -> None:
        """POST /internal/tasks/collect-source 단일 소스 수집."""
        with patch("src.api.internal_tasks.get_content_pipeline") as mock_get:
            mock_pipeline = MagicMock()
            # 반환값이 list[str]로 변경됨
            mock_pipeline._collect_from_source.return_value = [
                "cnt_001",
                "cnt_002",
                "cnt_003",
                "cnt_004",
                "cnt_005",
            ]
            mock_get.return_value = mock_pipeline

            with patch("src.api.internal_tasks.get_source_repo") as mock_repo_get:
                mock_repo = MagicMock()
                mock_source = MagicMock()
                mock_source.id = "src_001"
                mock_repo.get_by_id.return_value = mock_source
                mock_repo_get.return_value = mock_repo

                response = client.post(
                    "/internal/tasks/collect-source",
                    json={"source_id": "src_001"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["source_id"] == "src_001"
        assert data["collected"] == 5

    def test_collect_source_task_not_found(self, client: TestClient) -> None:
        """존재하지 않는 소스 수집 요청."""
        with patch("src.api.internal_tasks.get_source_repo") as mock_repo_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_get.return_value = mock_repo

            response = client.post(
                "/internal/tasks/collect-source",
                json={"source_id": "src_999"},
            )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
