"""Tests for RSS collection tool."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.agent.domains.collector.tools.rss_tool import (
    RSSEntry,
    fetch_rss,
    parse_rss_feed,
)


class TestParseRssFeed:
    """Tests for parse_rss_feed function."""

    @pytest.fixture
    def mock_feed_entry(self) -> dict[str, Any]:
        """Mock feedparser entry."""
        return {
            "title": "Test Article Title",
            "link": "https://example.com/article/1",
            "summary": "This is a test article summary.",
            "published_parsed": (2025, 12, 26, 9, 0, 0, 3, 360, 0),
            "id": "https://example.com/article/1",
        }

    def test_parse_valid_feed(self, mock_feed_entry: dict) -> None:
        """유효한 피드 파싱."""
        mock_feed = MagicMock()
        mock_feed.entries = [mock_feed_entry]
        mock_feed.bozo = False

        with patch(
            "src.agent.domains.collector.tools.rss_tool.feedparser.parse"
        ) as mock_parse:
            mock_parse.return_value = mock_feed

            entries = parse_rss_feed("https://example.com/feed.xml")

            assert len(entries) == 1
            assert entries[0].title == "Test Article Title"
            assert entries[0].url == "https://example.com/article/1"

    def test_parse_feed_with_content(self, mock_feed_entry: dict) -> None:
        """content 필드가 있는 피드 파싱."""
        mock_feed_entry["content"] = [{"value": "Full article content here."}]

        mock_feed = MagicMock()
        mock_feed.entries = [mock_feed_entry]
        mock_feed.bozo = False

        with patch(
            "src.agent.domains.collector.tools.rss_tool.feedparser.parse"
        ) as mock_parse:
            mock_parse.return_value = mock_feed

            entries = parse_rss_feed("https://example.com/feed.xml")

            assert entries[0].body == "Full article content here."

    def test_parse_feed_with_summary_fallback(self, mock_feed_entry: dict) -> None:
        """content 없을 때 summary 사용."""
        mock_feed = MagicMock()
        mock_feed.entries = [mock_feed_entry]
        mock_feed.bozo = False

        with patch(
            "src.agent.domains.collector.tools.rss_tool.feedparser.parse"
        ) as mock_parse:
            mock_parse.return_value = mock_feed

            entries = parse_rss_feed("https://example.com/feed.xml")

            assert entries[0].body == "This is a test article summary."

    def test_parse_feed_published_date(self, mock_feed_entry: dict) -> None:
        """발행일 파싱."""
        mock_feed = MagicMock()
        mock_feed.entries = [mock_feed_entry]
        mock_feed.bozo = False

        with patch(
            "src.agent.domains.collector.tools.rss_tool.feedparser.parse"
        ) as mock_parse:
            mock_parse.return_value = mock_feed

            entries = parse_rss_feed("https://example.com/feed.xml")

            assert entries[0].published_at is not None
            assert entries[0].published_at.year == 2025

    def test_parse_feed_no_published_date(self, mock_feed_entry: dict) -> None:
        """발행일 없는 경우."""
        del mock_feed_entry["published_parsed"]

        mock_feed = MagicMock()
        mock_feed.entries = [mock_feed_entry]
        mock_feed.bozo = False

        with patch(
            "src.agent.domains.collector.tools.rss_tool.feedparser.parse"
        ) as mock_parse:
            mock_parse.return_value = mock_feed

            entries = parse_rss_feed("https://example.com/feed.xml")

            assert entries[0].published_at is None

    def test_parse_empty_feed(self) -> None:
        """빈 피드."""
        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_feed.bozo = False

        with patch(
            "src.agent.domains.collector.tools.rss_tool.feedparser.parse"
        ) as mock_parse:
            mock_parse.return_value = mock_feed

            entries = parse_rss_feed("https://example.com/feed.xml")

            assert entries == []

    def test_parse_malformed_feed(self) -> None:
        """잘못된 형식의 피드."""
        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Invalid XML")

        with patch(
            "src.agent.domains.collector.tools.rss_tool.feedparser.parse"
        ) as mock_parse:
            mock_parse.return_value = mock_feed

            with pytest.raises(ValueError) as exc_info:
                parse_rss_feed("https://example.com/bad-feed.xml")

            assert "Failed to parse RSS" in str(exc_info.value)

    def test_parse_limit_entries(self, mock_feed_entry: dict) -> None:
        """엔트리 수 제한."""
        mock_feed = MagicMock()
        # 10개의 엔트리 생성
        mock_feed.entries = [
            {**mock_feed_entry, "title": f"Article {i}"} for i in range(10)
        ]
        mock_feed.bozo = False

        with patch(
            "src.agent.domains.collector.tools.rss_tool.feedparser.parse"
        ) as mock_parse:
            mock_parse.return_value = mock_feed

            entries = parse_rss_feed("https://example.com/feed.xml", limit=5)

            assert len(entries) == 5


class TestFetchRss:
    """Tests for fetch_rss tool function."""

    @pytest.fixture
    def mock_content_repo(self) -> MagicMock:
        """Mock ContentRepository."""
        return MagicMock()

    @pytest.fixture
    def sample_entries(self) -> list[RSSEntry]:
        """샘플 RSS 엔트리 목록."""
        return [
            RSSEntry(
                title="Article 1",
                url="https://example.com/article/1",
                body="Content 1",
                published_at=datetime.now(UTC),
            ),
            RSSEntry(
                title="Article 2",
                url="https://example.com/article/2",
                body="Content 2",
                published_at=datetime.now(UTC),
            ),
        ]

    def test_fetch_rss_new_contents(
        self,
        mock_content_repo: MagicMock,
        sample_entries: list[RSSEntry],
    ) -> None:
        """새 콘텐츠 수집."""
        mock_content_repo.exists_by_content_key.return_value = False

        with patch(
            "src.agent.domains.collector.tools.rss_tool.parse_rss_feed"
        ) as mock_parse:
            mock_parse.return_value = sample_entries

            results = fetch_rss(
                source_id="src_001",
                source_url="https://example.com/feed.xml",
                content_repo=mock_content_repo,
            )

            assert len(results) == 2
            assert mock_content_repo.create.call_count == 2

    def test_fetch_rss_skip_duplicates(
        self,
        mock_content_repo: MagicMock,
        sample_entries: list[RSSEntry],
    ) -> None:
        """중복 콘텐츠 건너뛰기."""
        # 첫 번째 엔트리만 이미 존재
        mock_content_repo.exists_by_content_key.side_effect = [True, False]

        with patch(
            "src.agent.domains.collector.tools.rss_tool.parse_rss_feed"
        ) as mock_parse:
            mock_parse.return_value = sample_entries

            results = fetch_rss(
                source_id="src_001",
                source_url="https://example.com/feed.xml",
                content_repo=mock_content_repo,
            )

            assert len(results) == 1
            assert mock_content_repo.create.call_count == 1

    def test_fetch_rss_all_duplicates(
        self,
        mock_content_repo: MagicMock,
        sample_entries: list[RSSEntry],
    ) -> None:
        """모든 콘텐츠가 중복."""
        mock_content_repo.exists_by_content_key.return_value = True

        with patch(
            "src.agent.domains.collector.tools.rss_tool.parse_rss_feed"
        ) as mock_parse:
            mock_parse.return_value = sample_entries

            results = fetch_rss(
                source_id="src_001",
                source_url="https://example.com/feed.xml",
                content_repo=mock_content_repo,
            )

            assert len(results) == 0
            assert mock_content_repo.create.call_count == 0

    def test_fetch_rss_content_key_generation(
        self,
        mock_content_repo: MagicMock,
    ) -> None:
        """content_key 생성 확인."""
        entry = RSSEntry(
            title="Test",
            url="https://example.com/article?utm_source=twitter",
            body="Content",
            published_at=None,
        )
        mock_content_repo.exists_by_content_key.return_value = False

        with patch(
            "src.agent.domains.collector.tools.rss_tool.parse_rss_feed"
        ) as mock_parse:
            mock_parse.return_value = [entry]

            fetch_rss(
                source_id="src_001",
                source_url="https://example.com/feed.xml",
                content_repo=mock_content_repo,
            )

            # create가 호출될 때 content_key가 설정되어 있어야 함
            call_args = mock_content_repo.create.call_args
            created_content = call_args[0][0]
            assert created_content.content_key.startswith("src_001:")

    def test_fetch_rss_error_handling(
        self,
        mock_content_repo: MagicMock,
    ) -> None:
        """피드 파싱 에러 처리."""
        with patch(
            "src.agent.domains.collector.tools.rss_tool.parse_rss_feed"
        ) as mock_parse:
            mock_parse.side_effect = ValueError("Failed to parse RSS")

            with pytest.raises(ValueError) as exc_info:
                fetch_rss(
                    source_id="src_001",
                    source_url="https://example.com/bad-feed.xml",
                    content_repo=mock_content_repo,
                )

            assert "Failed to parse RSS" in str(exc_info.value)
