"""Tests for DigestRepository."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.models.digest import DigestStatus
from src.repositories.digest_repo import DigestRepository


class TestDigestRepository:
    """Tests for DigestRepository."""

    @pytest.fixture
    def mock_firestore_client(self) -> MagicMock:
        """Mock FirestoreClient."""
        return MagicMock()

    @pytest.fixture
    def digest_repo(self, mock_firestore_client: MagicMock) -> DigestRepository:
        """DigestRepository 인스턴스."""
        return DigestRepository(mock_firestore_client)

    def test_collection_name(self, digest_repo: DigestRepository) -> None:
        """컬렉션 이름 확인."""
        assert digest_repo.collection_name == "digests"

    def test_get_by_digest_key(
        self,
        digest_repo: DigestRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """digest_key로 조회."""
        digest_data = {
            "id": "dgst_001",
            "subscription_id": "sub_001",
            "digest_key": "sub_001:2025-12-26",
            "digest_date": "2025-12-26",
            "content_ids": ["cnt_001", "cnt_002"],
            "content_count": 2,
            "channel_id": "C123456",
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_firestore_client.query.return_value = [digest_data]

        result = digest_repo.get_by_digest_key("sub_001:2025-12-26")

        assert result is not None
        assert result.digest_key == "sub_001:2025-12-26"

    def test_get_by_digest_key_not_found(
        self,
        digest_repo: DigestRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """digest_key 없는 경우."""
        mock_firestore_client.query.return_value = []

        result = digest_repo.get_by_digest_key("sub_001:2025-12-26")

        assert result is None

    def test_exists_by_digest_key(
        self,
        digest_repo: DigestRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """digest_key 존재 확인."""
        digest_data = {
            "id": "dgst_001",
            "subscription_id": "sub_001",
            "digest_key": "sub_001:2025-12-26",
            "digest_date": "2025-12-26",
            "content_ids": ["cnt_001"],
            "content_count": 1,
            "channel_id": "C123456",
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_firestore_client.query.return_value = [digest_data]

        result = digest_repo.exists_by_digest_key("sub_001:2025-12-26")

        assert result is True

    def test_find_by_subscription(
        self,
        digest_repo: DigestRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """구독별 다이제스트 조회."""
        digest_data = {
            "id": "dgst_001",
            "subscription_id": "sub_001",
            "digest_key": "sub_001:2025-12-26",
            "digest_date": "2025-12-26",
            "content_ids": ["cnt_001"],
            "content_count": 1,
            "channel_id": "C123456",
            "status": "sent",
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_firestore_client.query.return_value = [digest_data]

        results = digest_repo.find_by_subscription("sub_001")

        assert len(results) == 1
        assert results[0].subscription_id == "sub_001"

    def test_find_by_status(
        self,
        digest_repo: DigestRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """상태별 다이제스트 조회."""
        digest_data = {
            "id": "dgst_001",
            "subscription_id": "sub_001",
            "digest_key": "sub_001:2025-12-26",
            "digest_date": "2025-12-26",
            "content_ids": ["cnt_001"],
            "content_count": 1,
            "channel_id": "C123456",
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_firestore_client.query.return_value = [digest_data]

        results = digest_repo.find_by_status(DigestStatus.PENDING)

        assert len(results) == 1

    def test_update_status(
        self,
        digest_repo: DigestRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """상태 업데이트."""
        digest_repo.update_status("dgst_001", DigestStatus.SENT)

        mock_firestore_client.update.assert_called_once()
        call_args = mock_firestore_client.update.call_args
        assert call_args[0][0] == "digests"
        assert call_args[0][1] == "dgst_001"
        assert call_args[0][2]["status"] == DigestStatus.SENT.value

    def test_update_sent_info(
        self,
        digest_repo: DigestRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """발송 정보 업데이트."""
        message_ts = "1234567890.123456"

        digest_repo.update_sent_info("dgst_001", message_ts)

        mock_firestore_client.update.assert_called_once()
        call_args = mock_firestore_client.update.call_args
        update_data = call_args[0][2]
        assert update_data["slack_message_ts"] == message_ts
        assert update_data["status"] == DigestStatus.SENT.value
        assert "sent_at" in update_data

    def test_mark_as_failed(
        self,
        digest_repo: DigestRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """실패 마킹."""
        digest_repo.mark_as_failed("dgst_001", "Slack API error")

        mock_firestore_client.update.assert_called_once()
        call_args = mock_firestore_client.update.call_args
        update_data = call_args[0][2]
        assert update_data["status"] == DigestStatus.FAILED.value
        assert update_data["error"] == "Slack API error"

    def test_find_pending_for_sending(
        self,
        digest_repo: DigestRepository,
        mock_firestore_client: MagicMock,
    ) -> None:
        """발송 대기 다이제스트 조회."""
        digest_data = {
            "id": "dgst_001",
            "subscription_id": "sub_001",
            "digest_key": "sub_001:2025-12-26",
            "digest_date": "2025-12-26",
            "content_ids": ["cnt_001"],
            "content_count": 1,
            "channel_id": "C123456",
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
        }
        mock_firestore_client.query.return_value = [digest_data]

        results = digest_repo.find_pending_for_sending()

        assert len(results) == 1
        mock_firestore_client.query.assert_called_once()
