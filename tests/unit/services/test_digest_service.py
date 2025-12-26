"""Tests for DigestService."""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest

from src.models.content import Content, ProcessingStatus
from src.models.digest import Digest, DigestStatus
from src.models.subscription import (
    DeliveryFrequency,
    Subscription,
    SubscriptionPreferences,
)
from src.services.digest_service import DigestService


class TestDigestService:
    """Tests for DigestService."""

    @pytest.fixture
    def mock_content_repo(self) -> MagicMock:
        """Mock ContentRepository."""
        return MagicMock()

    @pytest.fixture
    def mock_digest_repo(self) -> MagicMock:
        """Mock DigestRepository."""
        return MagicMock()

    @pytest.fixture
    def mock_subscription_repo(self) -> MagicMock:
        """Mock SubscriptionRepository."""
        return MagicMock()

    @pytest.fixture
    def mock_slack_client(self) -> MagicMock:
        """Mock SlackClient."""
        client = MagicMock()
        client.post_message.return_value = {"ok": True, "ts": "1234567890.123456"}
        return client

    @pytest.fixture
    def digest_service(
        self,
        mock_content_repo: MagicMock,
        mock_digest_repo: MagicMock,
        mock_subscription_repo: MagicMock,
        mock_slack_client: MagicMock,
    ) -> DigestService:
        """DigestService 인스턴스."""
        return DigestService(
            content_repo=mock_content_repo,
            digest_repo=mock_digest_repo,
            subscription_repo=mock_subscription_repo,
            slack_client=mock_slack_client,
        )

    @pytest.fixture
    def sample_subscription(self) -> Subscription:
        """샘플 구독."""
        now = datetime.now(UTC)
        return Subscription(
            id="sub_001",
            platform="slack",
            platform_config={
                "team_id": "T123456",
                "channel_id": "C123456789",
            },
            preferences=SubscriptionPreferences(
                frequency=DeliveryFrequency.DAILY,
                delivery_time="09:00",
                categories=[],
                min_relevance=0.3,
                language="ko",
            ),
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    @pytest.fixture
    def sample_contents(self) -> list[Content]:
        """샘플 콘텐츠 리스트."""
        now = datetime.now(UTC)
        return [
            Content(
                id="cnt_001",
                source_id="src_001",
                content_key="src_001:abc123",
                original_url="https://example.com/article1",
                original_title="GPT-5 Released",
                original_body="OpenAI announced GPT-5.",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                title_ko="GPT-5 출시",
                summary_ko="OpenAI가 GPT-5를 발표했습니다.",
                why_important="LLM 발전에 중요합니다.",
                relevance_score=0.92,
                categories=["LLM"],
            ),
            Content(
                id="cnt_002",
                source_id="src_001",
                content_key="src_001:def456",
                original_url="https://example.com/article2",
                original_title="AI Regulation",
                original_body="EU announced new regulations.",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                title_ko="AI 규제",
                summary_ko="EU가 새로운 규제를 발표했습니다.",
                why_important="정책에 영향을 미칩니다.",
                relevance_score=0.78,
                categories=["Policy"],
            ),
        ]

    def test_create_digest_for_subscription(
        self,
        digest_service: DigestService,
        mock_content_repo: MagicMock,
        mock_digest_repo: MagicMock,
        sample_subscription: Subscription,
        sample_contents: list[Content],
    ) -> None:
        """구독에 대한 다이제스트 생성."""
        mock_content_repo.find_for_digest.return_value = sample_contents
        mock_digest_repo.exists_by_digest_key.return_value = False
        mock_digest_repo.create.return_value = None

        digest_date = date(2025, 12, 26)

        result = digest_service.create_digest(
            subscription=sample_subscription,
            digest_date=digest_date,
        )

        assert result is not None
        assert result.subscription_id == "sub_001"
        assert result.content_count == 2
        mock_digest_repo.create.assert_called_once()

    def test_create_digest_already_exists(
        self,
        digest_service: DigestService,
        mock_digest_repo: MagicMock,
        sample_subscription: Subscription,
    ) -> None:
        """이미 존재하는 다이제스트는 재생성하지 않음."""
        existing_digest = Digest(
            id="dgst_existing",
            subscription_id="sub_001",
            digest_key="sub_001:2025-12-26",
            digest_date=date(2025, 12, 26),
            content_ids=["cnt_001"],
            content_count=1,
            channel_id="C123456789",
            status=DigestStatus.SENT,
            created_at=datetime.now(UTC),
        )
        mock_digest_repo.exists_by_digest_key.return_value = True
        mock_digest_repo.get_by_digest_key.return_value = existing_digest

        digest_date = date(2025, 12, 26)

        result = digest_service.create_digest(
            subscription=sample_subscription,
            digest_date=digest_date,
        )

        # 기존 다이제스트 반환
        assert result.id == "dgst_existing"
        mock_digest_repo.create.assert_not_called()

    def test_create_digest_no_content(
        self,
        digest_service: DigestService,
        mock_content_repo: MagicMock,
        mock_digest_repo: MagicMock,
        sample_subscription: Subscription,
    ) -> None:
        """콘텐츠가 없어도 다이제스트 생성 (알림용)."""
        mock_content_repo.find_for_digest.return_value = []
        mock_digest_repo.exists_by_digest_key.return_value = False

        digest_date = date(2025, 12, 26)

        result = digest_service.create_digest(
            subscription=sample_subscription,
            digest_date=digest_date,
        )

        assert result is not None
        assert result.content_count == 0
        assert result.content_ids == []

    def test_send_digest_success(
        self,
        digest_service: DigestService,
        mock_content_repo: MagicMock,
        mock_digest_repo: MagicMock,
        mock_slack_client: MagicMock,
        sample_contents: list[Content],
    ) -> None:
        """다이제스트 발송 성공."""
        digest = Digest(
            id="dgst_001",
            subscription_id="sub_001",
            digest_key="sub_001:2025-12-26",
            digest_date=date(2025, 12, 26),
            content_ids=["cnt_001", "cnt_002"],
            content_count=2,
            channel_id="C123456789",
            status=DigestStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        mock_content_repo.find_by_ids.return_value = sample_contents

        result = digest_service.send_digest(digest)

        assert result is True
        mock_slack_client.post_message.assert_called_once()
        mock_digest_repo.update_sent_info.assert_called_once()

    def test_send_digest_failure(
        self,
        digest_service: DigestService,
        mock_content_repo: MagicMock,
        mock_digest_repo: MagicMock,
        mock_slack_client: MagicMock,
        sample_contents: list[Content],
    ) -> None:
        """다이제스트 발송 실패."""
        digest = Digest(
            id="dgst_001",
            subscription_id="sub_001",
            digest_key="sub_001:2025-12-26",
            digest_date=date(2025, 12, 26),
            content_ids=["cnt_001", "cnt_002"],
            content_count=2,
            channel_id="C123456789",
            status=DigestStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        mock_content_repo.find_by_ids.return_value = sample_contents
        mock_slack_client.post_message.side_effect = Exception("Slack error")

        result = digest_service.send_digest(digest)

        assert result is False
        mock_digest_repo.mark_as_failed.assert_called_once()

    def test_process_pending_digests(
        self,
        digest_service: DigestService,
        mock_content_repo: MagicMock,
        mock_digest_repo: MagicMock,
        mock_slack_client: MagicMock,
        sample_contents: list[Content],
    ) -> None:
        """대기 중인 다이제스트 일괄 처리."""
        pending_digests = [
            Digest(
                id="dgst_001",
                subscription_id="sub_001",
                digest_key="sub_001:2025-12-26",
                digest_date=date(2025, 12, 26),
                content_ids=["cnt_001"],
                content_count=1,
                channel_id="C123456789",
                status=DigestStatus.PENDING,
                created_at=datetime.now(UTC),
            ),
            Digest(
                id="dgst_002",
                subscription_id="sub_002",
                digest_key="sub_002:2025-12-26",
                digest_date=date(2025, 12, 26),
                content_ids=["cnt_002"],
                content_count=1,
                channel_id="C987654321",
                status=DigestStatus.PENDING,
                created_at=datetime.now(UTC),
            ),
        ]
        mock_digest_repo.find_pending_for_sending.return_value = pending_digests
        mock_content_repo.find_by_ids.return_value = sample_contents[:1]

        results = digest_service.process_pending_digests()

        assert results["total"] == 2
        assert results["sent"] == 2
        assert results["failed"] == 0

    def test_process_pending_digests_partial_failure(
        self,
        digest_service: DigestService,
        mock_content_repo: MagicMock,
        mock_digest_repo: MagicMock,
        mock_slack_client: MagicMock,
        sample_contents: list[Content],
    ) -> None:
        """일부 다이제스트 발송 실패."""
        pending_digests = [
            Digest(
                id="dgst_001",
                subscription_id="sub_001",
                digest_key="sub_001:2025-12-26",
                digest_date=date(2025, 12, 26),
                content_ids=["cnt_001"],
                content_count=1,
                channel_id="C123456789",
                status=DigestStatus.PENDING,
                created_at=datetime.now(UTC),
            ),
            Digest(
                id="dgst_002",
                subscription_id="sub_002",
                digest_key="sub_002:2025-12-26",
                digest_date=date(2025, 12, 26),
                content_ids=["cnt_002"],
                content_count=1,
                channel_id="C987654321",
                status=DigestStatus.PENDING,
                created_at=datetime.now(UTC),
            ),
        ]
        mock_digest_repo.find_pending_for_sending.return_value = pending_digests
        mock_content_repo.find_by_ids.return_value = sample_contents[:1]

        # 첫 번째 성공, 두 번째 실패
        mock_slack_client.post_message.side_effect = [
            {"ok": True, "ts": "1234567890.123456"},
            Exception("Channel not found"),
        ]

        results = digest_service.process_pending_digests()

        assert results["total"] == 2
        assert results["sent"] == 1
        assert results["failed"] == 1

    def test_get_due_subscriptions(
        self,
        digest_service: DigestService,
        mock_subscription_repo: MagicMock,
        sample_subscription: Subscription,
    ) -> None:
        """배송 시간에 맞는 구독 조회."""
        mock_subscription_repo.find_due_for_delivery.return_value = [
            sample_subscription
        ]

        result = digest_service.get_due_subscriptions("09:00")

        assert len(result) == 1
        assert result[0].id == "sub_001"
        mock_subscription_repo.find_due_for_delivery.assert_called_once_with("09:00")

    def test_create_and_send_for_subscription(
        self,
        digest_service: DigestService,
        mock_content_repo: MagicMock,
        mock_digest_repo: MagicMock,
        mock_slack_client: MagicMock,
        sample_subscription: Subscription,
        sample_contents: list[Content],
    ) -> None:
        """구독에 대한 다이제스트 생성 및 발송."""
        mock_content_repo.find_for_digest.return_value = sample_contents
        mock_content_repo.find_by_ids.return_value = sample_contents
        mock_digest_repo.exists_by_digest_key.return_value = False

        digest_date = date(2025, 12, 26)

        result = digest_service.create_and_send(
            subscription=sample_subscription,
            digest_date=digest_date,
        )

        assert result is True
        mock_digest_repo.create.assert_called_once()
        mock_slack_client.post_message.assert_called_once()

    def test_filter_contents_by_relevance(
        self,
        digest_service: DigestService,
        sample_contents: list[Content],
    ) -> None:
        """관련성 점수로 콘텐츠 필터링."""
        # min_relevance = 0.8 일 때
        filtered = digest_service._filter_by_relevance(
            contents=sample_contents,
            min_relevance=0.8,
        )

        # 0.92만 통과 (0.78은 탈락)
        assert len(filtered) == 1
        assert filtered[0].relevance_score == 0.92

    def test_sort_contents_by_score(
        self,
        digest_service: DigestService,
        sample_contents: list[Content],
    ) -> None:
        """관련성 점수로 콘텐츠 정렬."""
        sorted_contents = digest_service._sort_by_relevance(sample_contents)

        # 높은 점수 순
        assert sorted_contents[0].relevance_score == 0.92
        assert sorted_contents[1].relevance_score == 0.78
