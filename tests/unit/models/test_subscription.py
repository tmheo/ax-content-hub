"""Tests for Subscription model."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models.subscription import (
    DeliveryFrequency,
    Subscription,
    SubscriptionPreferences,
)


class TestDeliveryFrequency:
    """Tests for DeliveryFrequency enum."""

    def test_all_frequency_values(self) -> None:
        """모든 빈도 값 확인."""
        assert DeliveryFrequency.REALTIME == "realtime"
        assert DeliveryFrequency.DAILY == "daily"
        assert DeliveryFrequency.WEEKLY == "weekly"


class TestSubscriptionPreferences:
    """Tests for SubscriptionPreferences model."""

    def test_default_values(self) -> None:
        """기본값 확인."""
        prefs = SubscriptionPreferences()

        assert prefs.frequency == DeliveryFrequency.DAILY
        assert prefs.delivery_time == "09:00"
        assert prefs.categories == []
        assert prefs.min_relevance == 0.3
        assert prefs.language == "ko"

    def test_custom_values(self) -> None:
        """커스텀 값 설정."""
        prefs = SubscriptionPreferences(
            frequency=DeliveryFrequency.WEEKLY,
            delivery_time="18:00",
            categories=["AI_RESEARCH", "LLM"],
            min_relevance=0.5,
            language="en",
        )

        assert prefs.frequency == DeliveryFrequency.WEEKLY
        assert prefs.delivery_time == "18:00"
        assert prefs.categories == ["AI_RESEARCH", "LLM"]
        assert prefs.min_relevance == 0.5
        assert prefs.language == "en"

    def test_delivery_time_format_valid(self) -> None:
        """유효한 delivery_time 형식."""
        valid_times = ["00:00", "09:00", "12:30", "23:59"]
        for time in valid_times:
            prefs = SubscriptionPreferences(delivery_time=time)
            assert prefs.delivery_time == time

    def test_delivery_time_format_invalid(self) -> None:
        """잘못된 delivery_time 형식."""
        invalid_times = ["9:00", "25:00", "12:60", "noon", "9am"]
        for time in invalid_times:
            with pytest.raises(ValidationError):
                SubscriptionPreferences(delivery_time=time)

    def test_min_relevance_range(self) -> None:
        """min_relevance 범위 0.0~1.0 검증."""
        # 유효한 값
        prefs = SubscriptionPreferences(min_relevance=0.0)
        assert prefs.min_relevance == 0.0

        prefs = SubscriptionPreferences(min_relevance=1.0)
        assert prefs.min_relevance == 1.0

        # 범위 초과
        with pytest.raises(ValidationError):
            SubscriptionPreferences(min_relevance=1.5)

        with pytest.raises(ValidationError):
            SubscriptionPreferences(min_relevance=-0.1)


class TestSubscription:
    """Tests for Subscription model."""

    @pytest.fixture
    def valid_subscription_data(self) -> dict:
        """유효한 Subscription 데이터."""
        return {
            "id": "sub_001",
            "platform": "slack",
            "platform_config": {
                "team_id": "T12345",
                "channel_id": "C12345",
            },
            "preferences": SubscriptionPreferences(),
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

    def test_create_valid_subscription(self, valid_subscription_data: dict) -> None:
        """유효한 데이터로 Subscription 생성."""
        sub = Subscription(**valid_subscription_data)

        assert sub.id == "sub_001"
        assert sub.platform == "slack"
        assert sub.platform_config["team_id"] == "T12345"
        assert sub.platform_config["channel_id"] == "C12345"
        assert sub.is_active is True

    def test_default_platform(self, valid_subscription_data: dict) -> None:
        """기본 platform은 slack."""
        del valid_subscription_data["platform"]
        sub = Subscription(**valid_subscription_data)
        assert sub.platform == "slack"

    def test_default_is_active(self, valid_subscription_data: dict) -> None:
        """기본 is_active는 True."""
        del valid_subscription_data["is_active"]
        sub = Subscription(**valid_subscription_data)
        assert sub.is_active is True

    def test_channel_id_validation(self, valid_subscription_data: dict) -> None:
        """channel_id는 'C'로 시작해야 함."""
        valid_subscription_data["platform_config"]["channel_id"] = "invalid_channel"

        with pytest.raises(ValidationError) as exc_info:
            Subscription(**valid_subscription_data)

        assert "channel_id" in str(exc_info.value)

    def test_missing_platform_config_fields(self) -> None:
        """platform_config 필수 필드 누락."""
        with pytest.raises(ValidationError):
            Subscription(
                id="sub_002",
                platform_config={"team_id": "T12345"},  # channel_id 누락
                preferences=SubscriptionPreferences(),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

    def test_company_id_optional(self, valid_subscription_data: dict) -> None:
        """company_id는 선택적."""
        sub = Subscription(**valid_subscription_data)
        assert sub.company_id is None

        valid_subscription_data["company_id"] = "company_001"
        sub_with_company = Subscription(**valid_subscription_data)
        assert sub_with_company.company_id == "company_001"

    def test_preferences_nested_model(self, valid_subscription_data: dict) -> None:
        """preferences 중첩 모델 접근."""
        sub = Subscription(**valid_subscription_data)

        assert sub.preferences.frequency == DeliveryFrequency.DAILY
        assert sub.preferences.delivery_time == "09:00"
        assert sub.preferences.min_relevance == 0.3

    def test_preferences_from_dict(self, valid_subscription_data: dict) -> None:
        """dict로 preferences 설정."""
        valid_subscription_data["preferences"] = {
            "frequency": "weekly",
            "delivery_time": "18:00",
            "min_relevance": 0.5,
        }

        sub = Subscription(**valid_subscription_data)

        assert sub.preferences.frequency == DeliveryFrequency.WEEKLY
        assert sub.preferences.delivery_time == "18:00"

    def test_model_serialization(self, valid_subscription_data: dict) -> None:
        """모델 직렬화."""
        sub = Subscription(**valid_subscription_data)
        data = sub.model_dump()

        assert data["id"] == "sub_001"
        assert data["platform"] == "slack"
        assert data["preferences"]["frequency"] == "daily"
        assert data["platform_config"]["channel_id"] == "C12345"
