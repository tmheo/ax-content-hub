"""Tests for sources CRUD API endpoints."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.models.source import Source, SourceType


class TestSourcesEndpoints:
    """Tests for sources API endpoints."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """테스트용 FastAPI 앱."""
        from src.api.sources import router

        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """테스트 클라이언트."""
        return TestClient(app)

    @pytest.fixture
    def sample_source(self) -> Source:
        """샘플 소스."""
        now = datetime.now(UTC)
        return Source(
            id="src_001",
            name="TechCrunch",
            type=SourceType.RSS,
            url="https://techcrunch.com/feed/",
            category="TECH_NEWS",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    def test_list_sources(
        self,
        client: TestClient,
        sample_source: Source,
    ) -> None:
        """GET /sources 소스 목록 조회."""
        with patch("src.api.sources.get_source_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.find_all.return_value = [sample_source]
            mock_get.return_value = mock_repo

            response = client.get("/sources")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 1
        assert data["sources"][0]["id"] == "src_001"

    def test_list_sources_by_type(
        self,
        client: TestClient,
        sample_source: Source,
    ) -> None:
        """GET /sources?type=rss 타입별 소스 조회."""
        with patch("src.api.sources.get_source_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.find_by_type.return_value = [sample_source]
            mock_get.return_value = mock_repo

            response = client.get("/sources?type=rss")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 1

    def test_list_sources_active_only(
        self,
        client: TestClient,
        sample_source: Source,
    ) -> None:
        """GET /sources?active=true 활성 소스만 조회."""
        with patch("src.api.sources.get_source_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.find_active_sources.return_value = [sample_source]
            mock_get.return_value = mock_repo

            response = client.get("/sources?active=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 1

    def test_get_source(
        self,
        client: TestClient,
        sample_source: Source,
    ) -> None:
        """GET /sources/{source_id} 단일 소스 조회."""
        with patch("src.api.sources.get_source_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = sample_source
            mock_get.return_value = mock_repo

            response = client.get("/sources/src_001")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "src_001"
        assert data["name"] == "TechCrunch"

    def test_get_source_not_found(
        self,
        client: TestClient,
    ) -> None:
        """GET /sources/{source_id} 존재하지 않는 소스."""
        with patch("src.api.sources.get_source_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = None
            mock_get.return_value = mock_repo

            response = client.get("/sources/src_999")

        assert response.status_code == 404

    def test_create_source(
        self,
        client: TestClient,
    ) -> None:
        """POST /sources 새 소스 생성."""
        with patch("src.api.sources.get_source_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.create.return_value = None
            mock_get.return_value = mock_repo

            response = client.post(
                "/sources",
                json={
                    "name": "OpenAI Blog",
                    "type": "rss",
                    "url": "https://openai.com/blog/rss",
                    "category": "AI_RESEARCH",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "OpenAI Blog"
        assert data["type"] == "rss"
        mock_repo.create.assert_called_once()

    def test_create_source_invalid_type(
        self,
        client: TestClient,
    ) -> None:
        """POST /sources 잘못된 타입."""
        response = client.post(
            "/sources",
            json={
                "name": "Invalid",
                "type": "invalid_type",
                "url": "https://example.com",
            },
        )

        assert response.status_code == 422

    def test_update_source(
        self,
        client: TestClient,
        sample_source: Source,
    ) -> None:
        """PUT /sources/{source_id} 소스 수정."""
        with patch("src.api.sources.get_source_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = sample_source
            mock_repo.update.return_value = None
            mock_get.return_value = mock_repo

            response = client.put(
                "/sources/src_001",
                json={"name": "TechCrunch Updated"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TechCrunch Updated"

    def test_update_source_not_found(
        self,
        client: TestClient,
    ) -> None:
        """PUT /sources/{source_id} 존재하지 않는 소스 수정."""
        with patch("src.api.sources.get_source_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = None
            mock_get.return_value = mock_repo

            response = client.put(
                "/sources/src_999",
                json={"name": "Updated"},
            )

        assert response.status_code == 404

    def test_delete_source(
        self,
        client: TestClient,
        sample_source: Source,
    ) -> None:
        """DELETE /sources/{source_id} 소스 삭제."""
        with patch("src.api.sources.get_source_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = sample_source
            mock_repo.delete.return_value = None
            mock_get.return_value = mock_repo

            response = client.delete("/sources/src_001")

        assert response.status_code == 204
        mock_repo.delete.assert_called_once_with("src_001")

    def test_delete_source_not_found(
        self,
        client: TestClient,
    ) -> None:
        """DELETE /sources/{source_id} 존재하지 않는 소스 삭제."""
        with patch("src.api.sources.get_source_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = None
            mock_get.return_value = mock_repo

            response = client.delete("/sources/src_999")

        assert response.status_code == 404

    def test_activate_source(
        self,
        client: TestClient,
        sample_source: Source,
    ) -> None:
        """POST /sources/{source_id}/activate 소스 활성화."""
        inactive_source = sample_source.model_copy()
        inactive_source.is_active = False

        with patch("src.api.sources.get_source_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = inactive_source
            mock_repo.update.return_value = None
            mock_get.return_value = mock_repo

            response = client.post("/sources/src_001/activate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    def test_deactivate_source(
        self,
        client: TestClient,
        sample_source: Source,
    ) -> None:
        """POST /sources/{source_id}/deactivate 소스 비활성화."""
        with patch("src.api.sources.get_source_repo") as mock_get:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = sample_source
            mock_repo.deactivate.return_value = None
            mock_get.return_value = mock_repo

            response = client.post("/sources/src_001/deactivate")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        mock_repo.deactivate.assert_called_once_with("src_001")
