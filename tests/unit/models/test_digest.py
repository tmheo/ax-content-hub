"""Tests for Digest model."""

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from src.models.digest import Digest, DigestStatus, generate_digest_key


class TestGenerateDigestKey:
    """Tests for digest key generation."""

    def test_generate_key_format(self) -> None:
        """키 형식: {subscription_id}:{YYYY-MM-DD}."""
        key = generate_digest_key("sub_001", date(2025, 12, 26))
        assert key == "sub_001:2025-12-26"

    def test_same_subscription_same_date(self) -> None:
        """동일 구독+날짜는 동일 키."""
        d = date(2025, 12, 26)
        key1 = generate_digest_key("sub_001", d)
        key2 = generate_digest_key("sub_001", d)
        assert key1 == key2

    def test_different_date_different_key(self) -> None:
        """다른 날짜는 다른 키."""
        key1 = generate_digest_key("sub_001", date(2025, 12, 26))
        key2 = generate_digest_key("sub_001", date(2025, 12, 27))
        assert key1 != key2

    def test_different_subscription_different_key(self) -> None:
        """다른 구독은 다른 키."""
        d = date(2025, 12, 26)
        key1 = generate_digest_key("sub_001", d)
        key2 = generate_digest_key("sub_002", d)
        assert key1 != key2


class TestDigest:
    """Tests for Digest model."""

    @pytest.fixture
    def valid_digest_data(self) -> dict:
        """유효한 Digest 데이터."""
        return {
            "id": "dig_001",
            "subscription_id": "sub_001",
            "digest_key": "sub_001:2025-12-26",
            "digest_date": date(2025, 12, 26),
            "content_ids": ["cnt_abc123", "cnt_def456"],
            "content_count": 2,
            "channel_id": "C123456789",
            "status": DigestStatus.PENDING,
            "created_at": datetime.now(UTC),
        }

    def test_create_valid_digest(self, valid_digest_data: dict) -> None:
        """유효한 데이터로 Digest 생성."""
        digest = Digest(**valid_digest_data)

        assert digest.id == "dig_001"
        assert digest.subscription_id == "sub_001"
        assert digest.digest_key == "sub_001:2025-12-26"
        assert digest.content_ids == ["cnt_abc123", "cnt_def456"]
        assert digest.content_count == 2

    def test_status_default_pending(self, valid_digest_data: dict) -> None:
        """기본 상태는 pending."""
        del valid_digest_data["status"]
        digest = Digest(**valid_digest_data)
        assert digest.status == DigestStatus.PENDING

    def test_slack_message_ts_optional(self, valid_digest_data: dict) -> None:
        """slack_message_ts는 선택적."""
        digest = Digest(**valid_digest_data)
        assert digest.slack_message_ts is None

        valid_digest_data["slack_message_ts"] = "1735203615.000100"
        digest_with_ts = Digest(**valid_digest_data)
        assert digest_with_ts.slack_message_ts == "1735203615.000100"

    def test_content_ids_not_empty_by_default(self) -> None:
        """content_ids 기본값은 빈 리스트가 아님 (직접 지정 필요)."""
        with pytest.raises(ValidationError):
            Digest(
                id="dig_002",
                subscription_id="sub_001",
                digest_key="sub_001:2025-12-26",
                digest_date=date(2025, 12, 26),
                content_count=0,
                channel_id="C123456789",
                created_at=datetime.now(UTC),
            )

    def test_empty_content_ids_allowed_for_no_content_notification(
        self, valid_digest_data: dict
    ) -> None:
        """'콘텐츠 없음' 알림용 빈 content_ids 허용."""
        valid_digest_data["content_ids"] = []
        valid_digest_data["content_count"] = 0

        digest = Digest(**valid_digest_data)
        assert digest.content_ids == []
        assert digest.content_count == 0

    def test_content_count_matches_ids(self, valid_digest_data: dict) -> None:
        """content_count는 content_ids 길이와 일치해야 함."""
        valid_digest_data["content_count"] = 5  # 실제로는 2개

        with pytest.raises(ValidationError) as exc_info:
            Digest(**valid_digest_data)

        assert "content_count" in str(exc_info.value)

    def test_digest_key_format(self) -> None:
        """digest_key 형식 검증: {subscription_id}:{YYYY-MM-DD}."""
        with pytest.raises(ValidationError):
            Digest(
                id="dig_003",
                subscription_id="sub_001",
                digest_key="invalid-key-format",
                digest_date=date(2025, 12, 26),
                content_ids=["cnt_001"],
                content_count=1,
                channel_id="C123456789",
                created_at=datetime.now(UTC),
            )

    def test_missing_required_fields(self) -> None:
        """필수 필드 누락 시 ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Digest(id="dig_004")

        errors = exc_info.value.errors()
        required_fields = {
            "subscription_id",
            "digest_key",
            "digest_date",
            "content_ids",
            "content_count",
            "channel_id",
            "created_at",
        }
        error_fields = {e["loc"][0] for e in errors}

        assert required_fields.issubset(error_fields)

    def test_model_serialization(self, valid_digest_data: dict) -> None:
        """모델 직렬화."""
        digest = Digest(**valid_digest_data)
        data = digest.model_dump()

        assert data["id"] == "dig_001"
        assert data["subscription_id"] == "sub_001"
        assert data["content_count"] == 2
        assert len(data["content_ids"]) == 2

    def test_model_json_serialization(self, valid_digest_data: dict) -> None:
        """JSON 직렬화."""
        digest = Digest(**valid_digest_data)
        json_str = digest.model_dump_json()

        assert "dig_001" in json_str
        assert "sub_001:2025-12-26" in json_str
