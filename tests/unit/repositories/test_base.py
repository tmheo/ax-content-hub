"""Tests for BaseRepository."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field

from src.repositories.base import BaseRepository


class SampleModel(BaseModel):
    """테스트용 샘플 모델."""

    id: str
    name: str
    value: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SampleRepository(BaseRepository[SampleModel]):
    """테스트용 샘플 Repository."""

    collection_name = "samples"
    model_class = SampleModel


class TestBaseRepository:
    """Tests for BaseRepository."""

    @pytest.fixture
    def mock_firestore(self) -> MagicMock:
        """Mock FirestoreClient."""
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_firestore: MagicMock) -> SampleRepository:
        """SampleRepository with mock Firestore."""
        return SampleRepository(mock_firestore)

    @pytest.fixture
    def sample_data(self) -> dict[str, Any]:
        """샘플 데이터."""
        return {
            "id": "sample_001",
            "name": "Test Sample",
            "value": 42,
            "created_at": datetime.now(UTC),
        }

    def test_get_by_id_found(
        self, repo: SampleRepository, mock_firestore: MagicMock, sample_data: dict
    ) -> None:
        """ID로 문서 조회 - 존재하는 경우."""
        mock_firestore.get.return_value = sample_data

        result = repo.get_by_id("sample_001")

        assert result is not None
        assert result.id == "sample_001"
        assert result.name == "Test Sample"
        mock_firestore.get.assert_called_once_with("samples", "sample_001")

    def test_get_by_id_not_found(
        self, repo: SampleRepository, mock_firestore: MagicMock
    ) -> None:
        """ID로 문서 조회 - 존재하지 않는 경우."""
        mock_firestore.get.return_value = None

        result = repo.get_by_id("nonexistent")

        assert result is None
        mock_firestore.get.assert_called_once_with("samples", "nonexistent")

    def test_create(self, repo: SampleRepository, mock_firestore: MagicMock) -> None:
        """문서 생성."""
        model = SampleModel(id="sample_002", name="New Sample", value=100)

        repo.create(model)

        mock_firestore.set.assert_called_once()
        call_args = mock_firestore.set.call_args
        assert call_args[0][0] == "samples"
        assert call_args[0][1] == "sample_002"
        assert call_args[0][2]["name"] == "New Sample"
        assert call_args[0][2]["value"] == 100

    def test_update(self, repo: SampleRepository, mock_firestore: MagicMock) -> None:
        """문서 업데이트."""
        model = SampleModel(id="sample_001", name="Updated Sample", value=200)

        repo.update(model)

        mock_firestore.set.assert_called_once()
        call_args = mock_firestore.set.call_args
        assert call_args[0][0] == "samples"
        assert call_args[0][1] == "sample_001"
        assert call_args[0][2]["name"] == "Updated Sample"

    def test_delete(self, repo: SampleRepository, mock_firestore: MagicMock) -> None:
        """문서 삭제."""
        repo.delete("sample_001")

        mock_firestore.delete.assert_called_once_with("samples", "sample_001")

    def test_find_by_filters(
        self, repo: SampleRepository, mock_firestore: MagicMock, sample_data: dict
    ) -> None:
        """필터로 문서 조회."""
        mock_firestore.query.return_value = [sample_data]

        filters = [("value", "==", 42)]
        results = repo.find_by(filters)

        assert len(results) == 1
        assert results[0].value == 42
        mock_firestore.query.assert_called_once_with("samples", filters)

    def test_find_by_empty_result(
        self, repo: SampleRepository, mock_firestore: MagicMock
    ) -> None:
        """필터 조회 - 결과 없음."""
        mock_firestore.query.return_value = []

        filters = [("value", ">", 1000)]
        results = repo.find_by(filters)

        assert results == []

    def test_find_all(
        self, repo: SampleRepository, mock_firestore: MagicMock, sample_data: dict
    ) -> None:
        """전체 문서 조회."""
        mock_firestore.query.return_value = [sample_data]

        results = repo.find_all()

        assert len(results) == 1
        mock_firestore.query.assert_called_once_with("samples", [])

    def test_exists(
        self, repo: SampleRepository, mock_firestore: MagicMock, sample_data: dict
    ) -> None:
        """문서 존재 여부 확인."""
        mock_firestore.get.return_value = sample_data

        assert repo.exists("sample_001") is True
        mock_firestore.get.assert_called_once_with("samples", "sample_001")

    def test_not_exists(
        self, repo: SampleRepository, mock_firestore: MagicMock
    ) -> None:
        """문서 존재하지 않음 확인."""
        mock_firestore.get.return_value = None

        assert repo.exists("nonexistent") is False

    def test_count(
        self, repo: SampleRepository, mock_firestore: MagicMock, sample_data: dict
    ) -> None:
        """문서 수 카운트."""
        mock_firestore.query.return_value = [sample_data, sample_data]

        filters = [("value", ">=", 0)]
        count = repo.count(filters)

        assert count == 2

    def test_model_to_dict_serialization(
        self, repo: SampleRepository, mock_firestore: MagicMock
    ) -> None:
        """모델 직렬화 시 datetime 처리."""
        now = datetime.now(UTC)
        model = SampleModel(id="sample_003", name="Datetime Test", created_at=now)

        repo.create(model)

        call_args = mock_firestore.set.call_args
        saved_data = call_args[0][2]
        assert isinstance(saved_data["created_at"], datetime)
