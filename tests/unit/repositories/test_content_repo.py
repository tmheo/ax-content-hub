"""Tests for ContentRepository."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.models.content import ProcessingStatus
from src.repositories.content_repo import ContentRepository


class TestContentRepository:
    """Tests for ContentRepository."""

    @pytest.fixture
    def mock_firestore(self) -> MagicMock:
        """Mock FirestoreClient."""
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_firestore: MagicMock) -> ContentRepository:
        """ContentRepository with mock Firestore."""
        return ContentRepository(mock_firestore)

    @pytest.fixture
    def sample_content_data(self) -> dict[str, Any]:
        """샘플 Content 데이터."""
        return {
            "id": "cnt_001",
            "source_id": "src_001",
            "content_key": "src_001:abcd1234",
            "original_url": "https://example.com/article",
            "original_title": "Test Article",
            "original_body": "Article body text",
            "original_language": "en",
            "original_published_at": datetime.now(UTC),
            "title_ko": None,
            "summary_ko": None,
            "why_important": None,
            "relevance_score": None,
            "categories": [],
            "processing_status": "pending",
            "processing_attempts": 0,
            "last_error": None,
            "collected_at": datetime.now(UTC),
            "processed_at": None,
        }

    def test_collection_name(self, repo: ContentRepository) -> None:
        """collection_name은 'contents'."""
        assert repo.collection_name == "contents"

    def test_get_by_content_key(
        self,
        repo: ContentRepository,
        mock_firestore: MagicMock,
        sample_content_data: dict,
    ) -> None:
        """content_key로 조회."""
        mock_firestore.query.return_value = [sample_content_data]

        result = repo.get_by_content_key("src_001:abcd1234")

        assert result is not None
        assert result.content_key == "src_001:abcd1234"
        mock_firestore.query.assert_called_once_with(
            "contents", [("content_key", "==", "src_001:abcd1234")]
        )

    def test_get_by_content_key_not_found(
        self, repo: ContentRepository, mock_firestore: MagicMock
    ) -> None:
        """content_key로 조회 - 없는 경우."""
        mock_firestore.query.return_value = []

        result = repo.get_by_content_key("nonexistent")

        assert result is None

    def test_exists_by_content_key(
        self,
        repo: ContentRepository,
        mock_firestore: MagicMock,
        sample_content_data: dict,
    ) -> None:
        """content_key 존재 여부 확인."""
        mock_firestore.query.return_value = [sample_content_data]

        assert repo.exists_by_content_key("src_001:abcd1234") is True

    def test_find_by_status(
        self,
        repo: ContentRepository,
        mock_firestore: MagicMock,
        sample_content_data: dict,
    ) -> None:
        """상태별 콘텐츠 조회."""
        mock_firestore.query.return_value = [sample_content_data]

        results = repo.find_by_status(ProcessingStatus.PENDING)

        assert len(results) == 1
        mock_firestore.query.assert_called_once_with(
            "contents", [("processing_status", "==", "pending")]
        )

    def test_find_by_source(
        self,
        repo: ContentRepository,
        mock_firestore: MagicMock,
        sample_content_data: dict,
    ) -> None:
        """소스별 콘텐츠 조회."""
        mock_firestore.query.return_value = [sample_content_data]

        results = repo.find_by_source("src_001")

        assert len(results) == 1
        mock_firestore.query.assert_called_once_with(
            "contents", [("source_id", "==", "src_001")]
        )

    def test_find_pending_for_processing(
        self,
        repo: ContentRepository,
        mock_firestore: MagicMock,
        sample_content_data: dict,
    ) -> None:
        """처리 대기 중인 콘텐츠 조회."""
        mock_firestore.query.return_value = [sample_content_data]

        results = repo.find_pending_for_processing(limit=10)

        assert len(results) == 1
        mock_firestore.query.assert_called_once()

    def test_find_for_digest(
        self, repo: ContentRepository, mock_firestore: MagicMock
    ) -> None:
        """다이제스트용 콘텐츠 조회."""
        completed_data = {
            **{
                "id": "cnt_001",
                "source_id": "src_001",
                "content_key": "src_001:abcd1234",
                "original_url": "https://example.com/article",
                "original_title": "Test Article",
                "collected_at": datetime.now(UTC),
            },
            "processing_status": "completed",
            "relevance_score": 0.8,
            "title_ko": "테스트 기사",
            "summary_ko": "요약 내용",
        }
        mock_firestore.query.return_value = [completed_data]

        results = repo.find_for_digest(min_relevance=0.5)

        assert len(results) == 1
        mock_firestore.query.assert_called_once()

    def test_update_processing_status(
        self, repo: ContentRepository, mock_firestore: MagicMock
    ) -> None:
        """처리 상태 업데이트."""
        repo.update_processing_status("cnt_001", ProcessingStatus.PROCESSING)

        mock_firestore.update.assert_called_once()
        call_args = mock_firestore.update.call_args
        assert call_args[0][0] == "contents"
        assert call_args[0][1] == "cnt_001"
        assert call_args[0][2]["processing_status"] == "processing"

    def test_update_processing_result(
        self, repo: ContentRepository, mock_firestore: MagicMock
    ) -> None:
        """처리 결과 업데이트."""
        repo.update_processing_result(
            content_id="cnt_001",
            title_ko="한글 제목",
            summary_ko="요약 내용",
            why_important="중요한 이유",
            relevance_score=0.85,
            categories=["AI", "ML"],
        )

        mock_firestore.update.assert_called_once()
        call_args = mock_firestore.update.call_args
        data = call_args[0][2]
        assert data["title_ko"] == "한글 제목"
        assert data["summary_ko"] == "요약 내용"
        assert data["relevance_score"] == 0.85
        assert data["processing_status"] == "completed"
        assert "processed_at" in data

    def test_increment_processing_attempts(
        self,
        repo: ContentRepository,
        mock_firestore: MagicMock,
        sample_content_data: dict,
    ) -> None:
        """처리 시도 횟수 증가."""
        mock_firestore.get.return_value = sample_content_data

        repo.increment_processing_attempts("cnt_001", error="Timeout")

        mock_firestore.update.assert_called_once()
        call_args = mock_firestore.update.call_args
        data = call_args[0][2]
        assert data["processing_attempts"] == 1
        assert data["last_error"] == "Timeout"

    def test_mark_as_failed(
        self, repo: ContentRepository, mock_firestore: MagicMock
    ) -> None:
        """실패 상태로 마킹."""
        repo.mark_as_failed("cnt_001", error="Max retries exceeded")

        mock_firestore.update.assert_called_once()
        call_args = mock_firestore.update.call_args
        data = call_args[0][2]
        assert data["processing_status"] == "failed"
        assert data["last_error"] == "Max retries exceeded"

    def test_mark_as_skipped(
        self, repo: ContentRepository, mock_firestore: MagicMock
    ) -> None:
        """건너뜀 상태로 마킹."""
        repo.mark_as_skipped("cnt_001", reason="No transcript")

        mock_firestore.update.assert_called_once()
        call_args = mock_firestore.update.call_args
        data = call_args[0][2]
        assert data["processing_status"] == "skipped"
        assert data["last_error"] == "No transcript"
