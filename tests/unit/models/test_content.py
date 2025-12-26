"""Tests for Content model."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models.content import (
    Content,
    ProcessingStatus,
    generate_content_key,
    normalize_url,
)


class TestProcessingStatus:
    """Tests for ProcessingStatus enum."""

    def test_all_status_values(self) -> None:
        """모든 상태 값 확인."""
        assert ProcessingStatus.PENDING == "pending"
        assert ProcessingStatus.PROCESSING == "processing"
        assert ProcessingStatus.COMPLETED == "completed"
        assert ProcessingStatus.FAILED == "failed"
        assert ProcessingStatus.SKIPPED == "skipped"
        assert ProcessingStatus.TIMEOUT == "timeout"


class TestNormalizeUrl:
    """Tests for URL normalization."""

    def test_lowercase_scheme_and_host(self) -> None:
        """scheme과 host 소문자화."""
        url = "HTTPS://EXAMPLE.COM/Path"
        normalized = normalize_url(url)
        assert normalized.startswith("https://example.com")

    def test_remove_trailing_slash(self) -> None:
        """trailing slash 제거."""
        url = "https://example.com/path/"
        normalized = normalize_url(url)
        assert not normalized.endswith("/")

    def test_remove_utm_parameters(self) -> None:
        """UTM 파라미터 제거."""
        url = "https://example.com/page?utm_source=twitter&utm_medium=social"
        normalized = normalize_url(url)
        assert "utm_source" not in normalized
        assert "utm_medium" not in normalized

    def test_remove_tracking_parameters(self) -> None:
        """추적 파라미터 제거."""
        url = "https://example.com/page?ref=homepage&fbclid=abc123&gclid=xyz"
        normalized = normalize_url(url)
        assert "ref=" not in normalized
        assert "fbclid" not in normalized
        assert "gclid" not in normalized

    def test_preserve_meaningful_query_params(self) -> None:
        """의미 있는 쿼리 파라미터 유지."""
        url = "https://example.com/search?q=test&page=2"
        normalized = normalize_url(url)
        assert "q=test" in normalized
        assert "page=2" in normalized

    def test_remove_fragment(self) -> None:
        """fragment 제거."""
        url = "https://example.com/page#section1"
        normalized = normalize_url(url)
        assert "#" not in normalized

    def test_idempotent(self) -> None:
        """정규화는 멱등성 보장."""
        url = "https://example.com/path?a=1"
        normalized1 = normalize_url(url)
        normalized2 = normalize_url(normalized1)
        assert normalized1 == normalized2


class TestGenerateContentKey:
    """Tests for content key generation."""

    def test_generate_key_format(self) -> None:
        """키 형식: {source_id}:{hash}."""
        key = generate_content_key("src_001", "https://example.com/article")
        assert key.startswith("src_001:")
        assert len(key) > len("src_001:")

    def test_same_url_same_key(self) -> None:
        """동일 URL은 동일 키 생성."""
        url = "https://example.com/article"
        key1 = generate_content_key("src_001", url)
        key2 = generate_content_key("src_001", url)
        assert key1 == key2

    def test_different_source_different_key(self) -> None:
        """다른 source_id는 다른 키 생성."""
        url = "https://example.com/article"
        key1 = generate_content_key("src_001", url)
        key2 = generate_content_key("src_002", url)
        assert key1 != key2

    def test_normalized_urls_same_key(self) -> None:
        """정규화된 URL은 동일 키 생성."""
        url1 = "https://example.com/article?utm_source=twitter"
        url2 = "https://example.com/article"
        key1 = generate_content_key("src_001", url1)
        key2 = generate_content_key("src_001", url2)
        assert key1 == key2

    def test_hash_length(self) -> None:
        """해시 길이는 16자."""
        key = generate_content_key("src_001", "https://example.com/article")
        hash_part = key.split(":")[1]
        assert len(hash_part) == 16


class TestContent:
    """Tests for Content model."""

    @pytest.fixture
    def valid_content_data(self) -> dict:
        """유효한 Content 데이터."""
        return {
            "id": "cnt_abc123",
            "source_id": "src_001",
            "content_key": "src_001:a1b2c3d4e5f6g7h8",
            "original_url": "https://openai.com/blog/gpt-5",
            "original_title": "Introducing GPT-5",
            "original_body": "Today we announce...",
            "original_language": "en",
            "original_published_at": datetime.now(UTC),
            "collected_at": datetime.now(UTC),
        }

    def test_create_valid_content(self, valid_content_data: dict) -> None:
        """유효한 데이터로 Content 생성."""
        content = Content(**valid_content_data)

        assert content.id == "cnt_abc123"
        assert content.source_id == "src_001"
        assert content.original_title == "Introducing GPT-5"

    def test_default_processing_status(self, valid_content_data: dict) -> None:
        """기본 processing_status는 PENDING."""
        content = Content(**valid_content_data)
        assert content.processing_status == ProcessingStatus.PENDING

    def test_default_values(self, valid_content_data: dict) -> None:
        """기본값 확인."""
        content = Content(**valid_content_data)

        assert content.title_ko is None
        assert content.summary_ko is None
        assert content.why_important is None
        assert content.relevance_score is None
        assert content.categories == []
        assert content.processing_attempts == 0
        assert content.last_error is None
        assert content.processed_at is None

    def test_processed_content(self, valid_content_data: dict) -> None:
        """처리 완료된 콘텐츠."""
        valid_content_data.update(
            {
                "title_ko": "GPT-5 공개: 추론 향상",
                "summary_ko": "OpenAI가 GPT-5를 공개했습니다.",
                "why_important": "기업 AI 도입 전략에 직접적 영향",
                "relevance_score": 0.95,
                "categories": ["AI_RESEARCH", "LLM"],
                "processing_status": ProcessingStatus.COMPLETED,
                "processed_at": datetime.now(UTC),
            }
        )

        content = Content(**valid_content_data)

        assert content.title_ko == "GPT-5 공개: 추론 향상"
        assert content.relevance_score == 0.95
        assert content.processing_status == ProcessingStatus.COMPLETED

    def test_title_ko_max_length(self, valid_content_data: dict) -> None:
        """title_ko 최대 길이 20자 검증."""
        valid_content_data["title_ko"] = "이것은 20자를 초과하는 매우 긴 제목입니다"

        with pytest.raises(ValidationError) as exc_info:
            Content(**valid_content_data)

        assert "title_ko" in str(exc_info.value)

    def test_relevance_score_range(self, valid_content_data: dict) -> None:
        """relevance_score 범위 0.0~1.0 검증."""
        # 범위 초과
        valid_content_data["relevance_score"] = 1.5
        with pytest.raises(ValidationError):
            Content(**valid_content_data)

        # 음수
        valid_content_data["relevance_score"] = -0.1
        with pytest.raises(ValidationError):
            Content(**valid_content_data)

        # 유효한 값
        valid_content_data["relevance_score"] = 0.5
        content = Content(**valid_content_data)
        assert content.relevance_score == 0.5

    def test_processing_attempts_limit(self, valid_content_data: dict) -> None:
        """processing_attempts 횟수 추적."""
        valid_content_data["processing_attempts"] = 3
        valid_content_data["processing_status"] = ProcessingStatus.FAILED
        valid_content_data["last_error"] = "Timeout after 30s"

        content = Content(**valid_content_data)

        assert content.processing_attempts == 3
        assert content.processing_status == ProcessingStatus.FAILED
        assert content.last_error == "Timeout after 30s"

    def test_missing_required_fields(self) -> None:
        """필수 필드 누락 시 ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Content(id="cnt_001")

        errors = exc_info.value.errors()
        required_fields = {
            "source_id",
            "content_key",
            "original_url",
            "original_title",
            "collected_at",
        }
        error_fields = {e["loc"][0] for e in errors}

        assert required_fields.issubset(error_fields)

    def test_model_serialization(self, valid_content_data: dict) -> None:
        """모델 직렬화."""
        content = Content(**valid_content_data)
        data = content.model_dump()

        assert data["id"] == "cnt_abc123"
        assert data["processing_status"] == "pending"
