"""Tests for SourceRepository."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.models.source import Source, SourceType
from src.repositories.source_repo import SourceRepository


class TestSourceRepository:
    """Tests for SourceRepository."""

    @pytest.fixture
    def mock_firestore(self) -> MagicMock:
        """Mock FirestoreClient."""
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_firestore: MagicMock) -> SourceRepository:
        """SourceRepository with mock Firestore."""
        return SourceRepository(mock_firestore)

    @pytest.fixture
    def sample_source_data(self) -> dict[str, Any]:
        """샘플 Source 데이터."""
        return {
            "id": "src_001",
            "name": "OpenAI Blog",
            "type": "rss",
            "url": "https://openai.com/blog/rss",
            "config": {},
            "category": "AI_RESEARCH",
            "language": "en",
            "is_active": True,
            "last_fetched_at": None,
            "fetch_error_count": 0,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

    def test_collection_name(self, repo: SourceRepository) -> None:
        """collection_name은 'sources'."""
        assert repo.collection_name == "sources"

    def test_get_by_id(
        self,
        repo: SourceRepository,
        mock_firestore: MagicMock,
        sample_source_data: dict,
    ) -> None:
        """ID로 Source 조회."""
        mock_firestore.get.return_value = sample_source_data

        result = repo.get_by_id("src_001")

        assert result is not None
        assert result.id == "src_001"
        assert result.name == "OpenAI Blog"
        assert result.type == SourceType.RSS

    def test_create_source(
        self, repo: SourceRepository, mock_firestore: MagicMock
    ) -> None:
        """Source 생성."""
        source = Source(
            id="src_002",
            name="New Source",
            type=SourceType.YOUTUBE,
            url="https://youtube.com/@channel",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        repo.create(source)

        mock_firestore.set.assert_called_once()
        call_args = mock_firestore.set.call_args
        assert call_args[0][0] == "sources"
        assert call_args[0][1] == "src_002"

    def test_find_active_sources(
        self,
        repo: SourceRepository,
        mock_firestore: MagicMock,
        sample_source_data: dict,
    ) -> None:
        """활성 소스 조회."""
        mock_firestore.query.return_value = [sample_source_data]

        results = repo.find_active_sources()

        assert len(results) == 1
        assert results[0].is_active is True
        mock_firestore.query.assert_called_once_with(
            "sources", [("is_active", "==", True)]
        )

    def test_find_by_type(
        self,
        repo: SourceRepository,
        mock_firestore: MagicMock,
        sample_source_data: dict,
    ) -> None:
        """타입별 소스 조회."""
        mock_firestore.query.return_value = [sample_source_data]

        results = repo.find_by_type(SourceType.RSS)

        assert len(results) == 1
        mock_firestore.query.assert_called_once_with("sources", [("type", "==", "rss")])

    def test_find_active_by_type(
        self,
        repo: SourceRepository,
        mock_firestore: MagicMock,
        sample_source_data: dict,
    ) -> None:
        """타입별 활성 소스 조회."""
        mock_firestore.query.return_value = [sample_source_data]

        results = repo.find_active_by_type(SourceType.RSS)

        assert len(results) == 1
        mock_firestore.query.assert_called_once_with(
            "sources",
            [("is_active", "==", True), ("type", "==", "rss")],
        )

    def test_update_last_fetched(
        self,
        repo: SourceRepository,
        mock_firestore: MagicMock,
        sample_source_data: dict,
    ) -> None:
        """마지막 수집 시간 업데이트."""
        mock_firestore.get.return_value = sample_source_data
        now = datetime.now(UTC)

        repo.update_last_fetched("src_001", now)

        mock_firestore.update.assert_called_once()
        call_args = mock_firestore.update.call_args
        assert call_args[0][0] == "sources"
        assert call_args[0][1] == "src_001"
        assert "last_fetched_at" in call_args[0][2]
        assert "updated_at" in call_args[0][2]

    def test_increment_error_count(
        self,
        repo: SourceRepository,
        mock_firestore: MagicMock,
        sample_source_data: dict,
    ) -> None:
        """에러 카운트 증가."""
        mock_firestore.get.return_value = sample_source_data

        repo.increment_error_count("src_001")

        mock_firestore.update.assert_called_once()
        call_args = mock_firestore.update.call_args
        assert call_args[0][2]["fetch_error_count"] == 1

    def test_reset_error_count(
        self, repo: SourceRepository, mock_firestore: MagicMock
    ) -> None:
        """에러 카운트 리셋."""
        repo.reset_error_count("src_001")

        mock_firestore.update.assert_called_once()
        call_args = mock_firestore.update.call_args
        assert call_args[0][2]["fetch_error_count"] == 0

    def test_deactivate_source(
        self, repo: SourceRepository, mock_firestore: MagicMock
    ) -> None:
        """소스 비활성화."""
        repo.deactivate("src_001")

        mock_firestore.update.assert_called_once()
        call_args = mock_firestore.update.call_args
        assert call_args[0][2]["is_active"] is False
