"""Tests for Source model."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models.source import Source, SourceType


class TestSourceType:
    """Tests for SourceType enum."""

    def test_rss_value(self) -> None:
        """RSS 타입 값 확인."""
        assert SourceType.RSS == "rss"
        assert SourceType.RSS.value == "rss"

    def test_youtube_value(self) -> None:
        """YouTube 타입 값 확인."""
        assert SourceType.YOUTUBE == "youtube"
        assert SourceType.YOUTUBE.value == "youtube"


class TestSource:
    """Tests for Source model."""

    @pytest.fixture
    def valid_source_data(self) -> dict:
        """유효한 Source 데이터."""
        return {
            "id": "src_001",
            "name": "OpenAI Blog",
            "type": SourceType.RSS,
            "url": "https://openai.com/blog/rss",
            "category": "AI_RESEARCH",
            "language": "en",
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

    def test_create_valid_source(self, valid_source_data: dict) -> None:
        """유효한 데이터로 Source 생성."""
        source = Source(**valid_source_data)

        assert source.id == "src_001"
        assert source.name == "OpenAI Blog"
        assert source.type == SourceType.RSS
        assert str(source.url) == "https://openai.com/blog/rss"
        assert source.category == "AI_RESEARCH"
        assert source.language == "en"
        assert source.is_active is True

    def test_create_youtube_source(self, valid_source_data: dict) -> None:
        """YouTube 타입 Source 생성."""
        valid_source_data["type"] = SourceType.YOUTUBE
        valid_source_data["url"] = "https://www.youtube.com/@aiexplained"

        source = Source(**valid_source_data)
        assert source.type == SourceType.YOUTUBE

    def test_default_values(self) -> None:
        """기본값 확인."""
        source = Source(
            id="src_002",
            name="Test Source",
            type=SourceType.RSS,
            url="https://example.com/rss",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert source.config == {}
        assert source.category is None
        assert source.language == "en"
        assert source.is_active is True
        assert source.last_fetched_at is None
        assert source.fetch_error_count == 0

    def test_optional_config(self, valid_source_data: dict) -> None:
        """선택적 config 필드."""
        valid_source_data["config"] = {"max_items": 10, "include_content": True}
        source = Source(**valid_source_data)

        assert source.config["max_items"] == 10
        assert source.config["include_content"] is True

    def test_missing_required_fields(self) -> None:
        """필수 필드 누락 시 ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Source(id="src_003")

        errors = exc_info.value.errors()
        required_fields = {"name", "type", "url", "created_at", "updated_at"}
        error_fields = {e["loc"][0] for e in errors}

        assert required_fields.issubset(error_fields)

    def test_invalid_url(self, valid_source_data: dict) -> None:
        """잘못된 URL 형식."""
        valid_source_data["url"] = "not-a-valid-url"

        with pytest.raises(ValidationError) as exc_info:
            Source(**valid_source_data)

        assert "url" in str(exc_info.value)

    def test_fetch_error_count_increment(self, valid_source_data: dict) -> None:
        """fetch_error_count 증가."""
        source = Source(**valid_source_data)
        assert source.fetch_error_count == 0

        # Model is immutable by default, but we can test validation
        valid_source_data["fetch_error_count"] = 3
        updated_source = Source(**valid_source_data)
        assert updated_source.fetch_error_count == 3

    def test_last_fetched_at_update(self, valid_source_data: dict) -> None:
        """last_fetched_at 업데이트."""
        fetch_time = datetime.now(UTC)
        valid_source_data["last_fetched_at"] = fetch_time

        source = Source(**valid_source_data)
        assert source.last_fetched_at == fetch_time

    def test_model_serialization(self, valid_source_data: dict) -> None:
        """모델 직렬화/역직렬화."""
        source = Source(**valid_source_data)
        data = source.model_dump()

        assert data["id"] == "src_001"
        assert data["type"] == "rss"
        assert isinstance(data["created_at"], datetime)

    def test_model_json_serialization(self, valid_source_data: dict) -> None:
        """JSON 직렬화."""
        source = Source(**valid_source_data)
        json_str = source.model_dump_json()

        assert "src_001" in json_str
        assert "OpenAI Blog" in json_str
        assert "rss" in json_str
