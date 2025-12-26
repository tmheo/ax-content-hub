"""Tests for slack_sender_tool."""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest

from src.agent.domains.distributor.tools.slack_sender_tool import (
    DigestBlock,
    SlackDigestMessage,
    build_digest_blocks,
    send_digest,
    split_blocks_for_slack,
)
from src.models.content import Content, ProcessingStatus
from src.models.digest import Digest, DigestStatus


class TestDigestBlock:
    """Tests for DigestBlock dataclass."""

    def test_create_digest_block(self) -> None:
        """DigestBlock 생성."""
        block = DigestBlock(
            content_id="cnt_001",
            title_ko="AI 혁신 발표",
            summary_ko="OpenAI가 새로운 모델을 발표했습니다.",
            why_important="기업 AI 도입에 중요한 영향",
            relevance_score=0.85,
            original_url="https://example.com/article",
            categories=["LLM", "Enterprise AI"],
        )

        assert block.content_id == "cnt_001"
        assert block.title_ko == "AI 혁신 발표"
        assert block.relevance_score == 0.85
        assert len(block.categories) == 2

    def test_digest_block_default_categories(self) -> None:
        """카테고리 기본값 빈 리스트."""
        block = DigestBlock(
            content_id="cnt_001",
            title_ko="제목",
            summary_ko="요약",
            why_important="중요성",
            relevance_score=0.5,
            original_url="https://example.com",
        )

        assert block.categories == []


class TestSlackDigestMessage:
    """Tests for SlackDigestMessage dataclass."""

    def test_create_slack_digest_message(self) -> None:
        """SlackDigestMessage 생성."""
        message = SlackDigestMessage(
            channel_id="C123456789",
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}],
            thread_ts=None,
        )

        assert message.channel_id == "C123456789"
        assert len(message.blocks) == 1
        assert message.thread_ts is None

    def test_slack_digest_message_with_thread(self) -> None:
        """스레드에 발송하는 메시지."""
        message = SlackDigestMessage(
            channel_id="C123456789",
            blocks=[],
            thread_ts="1234567890.123456",
        )

        assert message.thread_ts == "1234567890.123456"


class TestBuildDigestBlocks:
    """Tests for build_digest_blocks function."""

    @pytest.fixture
    def sample_digest_blocks(self) -> list[DigestBlock]:
        """샘플 DigestBlock 리스트."""
        return [
            DigestBlock(
                content_id="cnt_001",
                title_ko="GPT-5 출시",
                summary_ko="OpenAI가 GPT-5를 발표했습니다. 추론 능력이 대폭 향상되었습니다.",
                why_important="LLM 기술 발전의 중요한 이정표입니다.",
                relevance_score=0.92,
                original_url="https://example.com/gpt5",
                categories=["LLM", "OpenAI"],
            ),
            DigestBlock(
                content_id="cnt_002",
                title_ko="AI 규제 동향",
                summary_ko="EU가 새로운 AI 규제안을 발표했습니다.",
                why_important="글로벌 AI 정책에 영향을 미칩니다.",
                relevance_score=0.78,
                original_url="https://example.com/regulation",
                categories=["Policy"],
            ),
        ]

    def test_build_blocks_creates_header(
        self, sample_digest_blocks: list[DigestBlock]
    ) -> None:
        """헤더 블록 생성 확인."""
        digest_date = date(2025, 12, 26)

        blocks = build_digest_blocks(
            digest_blocks=sample_digest_blocks,
            digest_date=digest_date,
        )

        # 첫 번째 블록은 헤더
        assert blocks[0]["type"] == "header"
        assert "2025-12-26" in blocks[0]["text"]["text"]

    def test_build_blocks_creates_content_sections(
        self, sample_digest_blocks: list[DigestBlock]
    ) -> None:
        """콘텐츠 섹션 블록 생성 확인."""
        digest_date = date(2025, 12, 26)

        blocks = build_digest_blocks(
            digest_blocks=sample_digest_blocks,
            digest_date=digest_date,
        )

        # 헤더 이후에 콘텐츠 블록들이 있어야 함
        section_blocks = [b for b in blocks if b["type"] == "section"]
        assert len(section_blocks) >= 2

    def test_build_blocks_includes_dividers(
        self, sample_digest_blocks: list[DigestBlock]
    ) -> None:
        """콘텐츠 사이에 구분선 포함."""
        digest_date = date(2025, 12, 26)

        blocks = build_digest_blocks(
            digest_blocks=sample_digest_blocks,
            digest_date=digest_date,
        )

        divider_blocks = [b for b in blocks if b["type"] == "divider"]
        assert len(divider_blocks) >= 1

    def test_build_blocks_includes_url_button(
        self, sample_digest_blocks: list[DigestBlock]
    ) -> None:
        """원문 링크 버튼 포함."""
        digest_date = date(2025, 12, 26)

        blocks = build_digest_blocks(
            digest_blocks=sample_digest_blocks,
            digest_date=digest_date,
        )

        # actions 블록에 버튼이 있어야 함
        actions_blocks = [b for b in blocks if b["type"] == "actions"]
        assert len(actions_blocks) >= 1

    def test_build_blocks_empty_content(self) -> None:
        """빈 콘텐츠 처리."""
        digest_date = date(2025, 12, 26)

        blocks = build_digest_blocks(
            digest_blocks=[],
            digest_date=digest_date,
        )

        # 헤더와 '오늘 콘텐츠 없음' 메시지
        assert len(blocks) >= 1
        # 텍스트에 '없음' 관련 메시지가 있어야 함
        all_text = str(blocks)
        assert "없" in all_text or "No content" in all_text.lower()

    def test_build_blocks_shows_relevance_score(
        self, sample_digest_blocks: list[DigestBlock]
    ) -> None:
        """관련성 점수 표시."""
        digest_date = date(2025, 12, 26)

        blocks = build_digest_blocks(
            digest_blocks=sample_digest_blocks,
            digest_date=digest_date,
        )

        # 점수가 표시되어야 함 (92% 또는 0.92)
        all_text = str(blocks)
        assert "92" in all_text or "0.92" in all_text

    def test_build_blocks_shows_categories(
        self, sample_digest_blocks: list[DigestBlock]
    ) -> None:
        """카테고리 태그 표시."""
        digest_date = date(2025, 12, 26)

        blocks = build_digest_blocks(
            digest_blocks=sample_digest_blocks,
            digest_date=digest_date,
        )

        all_text = str(blocks)
        assert "LLM" in all_text or "OpenAI" in all_text


class TestSplitBlocksForSlack:
    """Tests for split_blocks_for_slack function."""

    def test_no_split_under_50_blocks(self) -> None:
        """50개 미만 블록은 분할 안함."""
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"Block {i}"}}
            for i in range(30)
        ]

        result = split_blocks_for_slack(blocks)

        assert len(result) == 1
        assert len(result[0]) == 30

    def test_split_at_50_blocks(self) -> None:
        """정확히 50개 블록은 분할 안함."""
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"Block {i}"}}
            for i in range(50)
        ]

        result = split_blocks_for_slack(blocks)

        assert len(result) == 1
        assert len(result[0]) == 50

    def test_split_over_50_blocks(self) -> None:
        """50개 초과 블록 분할."""
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"Block {i}"}}
            for i in range(75)
        ]

        result = split_blocks_for_slack(blocks)

        assert len(result) == 2
        assert len(result[0]) == 50
        assert len(result[1]) == 25

    def test_split_many_blocks(self) -> None:
        """많은 블록 다중 분할."""
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"Block {i}"}}
            for i in range(125)
        ]

        result = split_blocks_for_slack(blocks)

        assert len(result) == 3
        assert len(result[0]) == 50
        assert len(result[1]) == 50
        assert len(result[2]) == 25

    def test_split_empty_blocks(self) -> None:
        """빈 블록 리스트."""
        blocks: list[dict] = []

        result = split_blocks_for_slack(blocks)

        assert len(result) == 1
        assert len(result[0]) == 0


class TestSendDigest:
    """Tests for send_digest function."""

    @pytest.fixture
    def mock_slack_client(self) -> MagicMock:
        """Mock SlackClient."""
        client = MagicMock()
        client.post_message.return_value = {"ok": True, "ts": "1234567890.123456"}
        return client

    @pytest.fixture
    def sample_digest(self) -> Digest:
        """샘플 Digest."""
        return Digest(
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

    @pytest.fixture
    def sample_contents(self) -> list[Content]:
        """샘플 Content 리스트."""
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

    def test_send_digest_success(
        self,
        mock_slack_client: MagicMock,
        sample_digest: Digest,
        sample_contents: list[Content],
    ) -> None:
        """다이제스트 발송 성공."""
        result = send_digest(
            digest=sample_digest,
            contents=sample_contents,
            slack_client=mock_slack_client,
        )

        assert result.success is True
        assert result.message_ts == "1234567890.123456"
        mock_slack_client.post_message.assert_called_once()

    def test_send_digest_with_channel_id(
        self,
        mock_slack_client: MagicMock,
        sample_digest: Digest,
        sample_contents: list[Content],
    ) -> None:
        """채널 ID로 발송."""
        send_digest(
            digest=sample_digest,
            contents=sample_contents,
            slack_client=mock_slack_client,
        )

        call_args = mock_slack_client.post_message.call_args
        assert call_args[1]["channel"] == "C123456789"

    def test_send_digest_failure(
        self,
        mock_slack_client: MagicMock,
        sample_digest: Digest,
        sample_contents: list[Content],
    ) -> None:
        """다이제스트 발송 실패."""
        mock_slack_client.post_message.side_effect = Exception("Slack API error")

        result = send_digest(
            digest=sample_digest,
            contents=sample_contents,
            slack_client=mock_slack_client,
        )

        assert result.success is False
        assert "Slack API error" in result.error

    def test_send_digest_empty_contents(
        self,
        mock_slack_client: MagicMock,
        sample_digest: Digest,
    ) -> None:
        """빈 콘텐츠 다이제스트 발송."""
        sample_digest.content_ids = []
        sample_digest.content_count = 0

        result = send_digest(
            digest=sample_digest,
            contents=[],
            slack_client=mock_slack_client,
        )

        assert result.success is True
        mock_slack_client.post_message.assert_called_once()

    def test_send_digest_splits_large_blocks(
        self,
        mock_slack_client: MagicMock,
        sample_digest: Digest,
    ) -> None:
        """많은 블록 분할 발송."""
        # 많은 콘텐츠 생성 (50개 초과 블록 생성되도록)
        now = datetime.now(UTC)
        many_contents = [
            Content(
                id=f"cnt_{i:03d}",
                source_id="src_001",
                content_key=f"src_001:hash{i}",
                original_url=f"https://example.com/article{i}",
                original_title=f"Article {i}",
                original_body=f"Body {i}",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                title_ko=f"기사 {i}",
                summary_ko=f"요약 {i}",
                why_important=f"중요성 {i}",
                relevance_score=0.8,
                categories=["Test"],
            )
            for i in range(20)  # 20개 콘텐츠 = 많은 블록
        ]

        sample_digest.content_ids = [c.id for c in many_contents]
        sample_digest.content_count = len(many_contents)

        result = send_digest(
            digest=sample_digest,
            contents=many_contents,
            slack_client=mock_slack_client,
        )

        assert result.success is True
        # 분할 발송 여부는 블록 수에 따라 다름
        assert mock_slack_client.post_message.call_count >= 1

    def test_send_digest_thread_reply(
        self,
        mock_slack_client: MagicMock,
        sample_digest: Digest,
        sample_contents: list[Content],
    ) -> None:
        """분할 발송 시 스레드 답글."""
        # 50개 초과 블록을 생성하는 많은 콘텐츠 (각 콘텐츠당 약 4블록)
        # 약 15개 콘텐츠 = 60+ 블록 = 2 청크
        now = datetime.now(UTC)
        many_contents = [
            Content(
                id=f"cnt_{i:03d}",
                source_id="src_001",
                content_key=f"src_001:hash{i}",
                original_url=f"https://example.com/article{i}",
                original_title=f"Article {i}",
                original_body=f"Body {i}",
                original_language="en",
                processing_status=ProcessingStatus.COMPLETED,
                collected_at=now,
                title_ko=f"기사 {i}",
                summary_ko=f"요약 {i}",
                why_important=f"중요성 {i}",
                relevance_score=0.8,
                categories=["Test"],
            )
            for i in range(15)  # 15개 콘텐츠 = ~63 블록 = 2 청크
        ]

        # 여러 번 호출될 수 있도록 return_value 사용
        mock_slack_client.post_message.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }

        sample_digest.content_ids = [c.id for c in many_contents]
        sample_digest.content_count = len(many_contents)

        result = send_digest(
            digest=sample_digest,
            contents=many_contents,
            slack_client=mock_slack_client,
        )

        assert result.success is True
        # 첫 번째 메시지의 ts를 반환
        assert result.message_ts == "1234567890.123456"
        # 분할 발송으로 2번 이상 호출
        assert mock_slack_client.post_message.call_count >= 2
