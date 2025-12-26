"""Tests for YouTube transcript collection tool."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.agent.domains.collector.tools.youtube_tool import (
    YouTubeTranscript,
    extract_video_id,
    fetch_youtube,
    get_transcript,
)


class TestExtractVideoId:
    """Tests for extract_video_id function."""

    def test_extract_from_standard_url(self) -> None:
        """표준 YouTube URL에서 ID 추출."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_from_short_url(self) -> None:
        """youtu.be 단축 URL에서 ID 추출."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_from_embed_url(self) -> None:
        """embed URL에서 ID 추출."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_from_url_with_params(self) -> None:
        """추가 파라미터가 있는 URL에서 ID 추출."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_from_url_with_timestamp(self) -> None:
        """타임스탬프가 있는 URL에서 ID 추출."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_from_shorts_url(self) -> None:
        """Shorts URL에서 ID 추출."""
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_raw_video_id(self) -> None:
        """순수 video ID 입력."""
        video_id = "dQw4w9WgXcQ"
        assert extract_video_id(video_id) == "dQw4w9WgXcQ"

    def test_extract_invalid_url(self) -> None:
        """잘못된 URL."""
        url = "https://example.com/video"
        assert extract_video_id(url) is None

    def test_extract_empty_string(self) -> None:
        """빈 문자열."""
        assert extract_video_id("") is None


class TestGetTranscript:
    """Tests for get_transcript function."""

    def test_get_english_transcript(self) -> None:
        """영어 자막 가져오기."""
        mock_transcript_data = [
            {"text": "Hello world.", "start": 0.0, "duration": 2.0},
            {"text": "This is a test.", "start": 2.0, "duration": 2.0},
        ]

        with patch(
            "src.agent.domains.collector.tools.youtube_tool.YouTubeTranscriptApi"
        ) as mock_api:
            mock_api.get_transcript.return_value = mock_transcript_data

            result = get_transcript("dQw4w9WgXcQ")

            assert result is not None
            assert result.video_id == "dQw4w9WgXcQ"
            assert "Hello world" in result.text
            assert "This is a test" in result.text
            assert result.language == "en"

    def test_get_korean_transcript(self) -> None:
        """한국어 자막 가져오기."""
        mock_transcript_data = [
            {"text": "안녕하세요.", "start": 0.0, "duration": 2.0},
            {"text": "테스트입니다.", "start": 2.0, "duration": 2.0},
        ]

        with patch(
            "src.agent.domains.collector.tools.youtube_tool.YouTubeTranscriptApi"
        ) as mock_api:
            mock_api.get_transcript.return_value = mock_transcript_data

            result = get_transcript("dQw4w9WgXcQ", languages=["ko"])

            assert result is not None
            assert "안녕하세요" in result.text
            mock_api.get_transcript.assert_called_once_with(
                "dQw4w9WgXcQ", languages=["ko"]
            )

    def test_get_transcript_fallback_languages(self) -> None:
        """언어 폴백 테스트."""
        mock_transcript_data = [
            {"text": "Fallback content.", "start": 0.0, "duration": 2.0},
        ]

        with patch(
            "src.agent.domains.collector.tools.youtube_tool.YouTubeTranscriptApi"
        ) as mock_api:
            mock_api.get_transcript.return_value = mock_transcript_data

            result = get_transcript("dQw4w9WgXcQ", languages=["ko", "en"])

            assert result is not None
            mock_api.get_transcript.assert_called_once_with(
                "dQw4w9WgXcQ", languages=["ko", "en"]
            )

    def test_get_transcript_no_transcript_available(self) -> None:
        """자막 없는 경우."""
        with patch(
            "src.agent.domains.collector.tools.youtube_tool.YouTubeTranscriptApi"
        ) as mock_api:
            from youtube_transcript_api._errors import TranscriptsDisabled

            mock_api.get_transcript.side_effect = TranscriptsDisabled("video_id")

            result = get_transcript("dQw4w9WgXcQ")

            assert result is None

    def test_get_transcript_api_error(self) -> None:
        """API 에러."""
        with patch(
            "src.agent.domains.collector.tools.youtube_tool.YouTubeTranscriptApi"
        ) as mock_api:
            mock_api.get_transcript.side_effect = Exception("API Error")

            result = get_transcript("dQw4w9WgXcQ")

            assert result is None

    def test_get_transcript_concatenates_text(self) -> None:
        """여러 세그먼트 텍스트 연결."""
        mock_transcript_data = [
            {"text": "First segment.", "start": 0.0, "duration": 1.0},
            {"text": "Second segment.", "start": 1.0, "duration": 1.0},
            {"text": "Third segment.", "start": 2.0, "duration": 1.0},
        ]

        with patch(
            "src.agent.domains.collector.tools.youtube_tool.YouTubeTranscriptApi"
        ) as mock_api:
            mock_api.get_transcript.return_value = mock_transcript_data

            result = get_transcript("dQw4w9WgXcQ")

            assert result is not None
            assert "First segment" in result.text
            assert "Second segment" in result.text
            assert "Third segment" in result.text

    def test_get_transcript_duration(self) -> None:
        """자막 전체 길이 계산."""
        mock_transcript_data = [
            {"text": "First.", "start": 0.0, "duration": 2.0},
            {"text": "Last.", "start": 58.0, "duration": 2.0},
        ]

        with patch(
            "src.agent.domains.collector.tools.youtube_tool.YouTubeTranscriptApi"
        ) as mock_api:
            mock_api.get_transcript.return_value = mock_transcript_data

            result = get_transcript("dQw4w9WgXcQ")

            assert result is not None
            assert result.duration_seconds == 60.0  # 58.0 + 2.0


class TestFetchYoutube:
    """Tests for fetch_youtube tool function."""

    @pytest.fixture
    def mock_content_repo(self) -> MagicMock:
        """Mock ContentRepository."""
        return MagicMock()

    @pytest.fixture
    def sample_transcript(self) -> YouTubeTranscript:
        """샘플 자막 객체."""
        return YouTubeTranscript(
            video_id="dQw4w9WgXcQ",
            text="This is a sample transcript for testing.",
            language="en",
            duration_seconds=180.0,
        )

    def test_fetch_youtube_new_content(
        self,
        mock_content_repo: MagicMock,
        sample_transcript: YouTubeTranscript,
    ) -> None:
        """새 콘텐츠 수집."""
        mock_content_repo.exists_by_content_key.return_value = False

        with patch(
            "src.agent.domains.collector.tools.youtube_tool.get_transcript"
        ) as mock_get:
            mock_get.return_value = sample_transcript

            result = fetch_youtube(
                source_id="src_youtube",
                video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                video_title="Test Video Title",
                content_repo=mock_content_repo,
            )

            assert result is not None
            assert result.source_id == "src_youtube"
            assert result.original_title == "Test Video Title"
            mock_content_repo.create.assert_called_once()

    def test_fetch_youtube_duplicate_content(
        self,
        mock_content_repo: MagicMock,
        sample_transcript: YouTubeTranscript,
    ) -> None:
        """중복 콘텐츠는 None 반환."""
        mock_content_repo.exists_by_content_key.return_value = True

        with patch(
            "src.agent.domains.collector.tools.youtube_tool.get_transcript"
        ) as mock_get:
            mock_get.return_value = sample_transcript

            result = fetch_youtube(
                source_id="src_youtube",
                video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                video_title="Test Video",
                content_repo=mock_content_repo,
            )

            assert result is None
            mock_content_repo.create.assert_not_called()

    def test_fetch_youtube_no_transcript(
        self,
        mock_content_repo: MagicMock,
    ) -> None:
        """자막 없는 경우 None 반환."""
        with patch(
            "src.agent.domains.collector.tools.youtube_tool.get_transcript"
        ) as mock_get:
            mock_get.return_value = None

            result = fetch_youtube(
                source_id="src_youtube",
                video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                video_title="No Transcript Video",
                content_repo=mock_content_repo,
            )

            assert result is None
            mock_content_repo.create.assert_not_called()

    def test_fetch_youtube_invalid_url(
        self,
        mock_content_repo: MagicMock,
    ) -> None:
        """잘못된 URL은 ValueError."""
        with pytest.raises(ValueError) as exc_info:
            fetch_youtube(
                source_id="src_youtube",
                video_url="https://example.com/not-youtube",
                video_title="Invalid",
                content_repo=mock_content_repo,
            )

        assert "Invalid YouTube URL" in str(exc_info.value)

    def test_fetch_youtube_content_key_generation(
        self,
        mock_content_repo: MagicMock,
        sample_transcript: YouTubeTranscript,
    ) -> None:
        """content_key 생성 확인."""
        mock_content_repo.exists_by_content_key.return_value = False

        with patch(
            "src.agent.domains.collector.tools.youtube_tool.get_transcript"
        ) as mock_get:
            mock_get.return_value = sample_transcript

            fetch_youtube(
                source_id="src_youtube",
                video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                video_title="Test Video",
                content_repo=mock_content_repo,
            )

            call_args = mock_content_repo.create.call_args
            created_content = call_args[0][0]
            assert created_content.content_key.startswith("src_youtube:")

    def test_fetch_youtube_with_published_at(
        self,
        mock_content_repo: MagicMock,
        sample_transcript: YouTubeTranscript,
    ) -> None:
        """발행일 전달."""
        mock_content_repo.exists_by_content_key.return_value = False
        published_at = datetime(2025, 12, 26, 10, 0, 0, tzinfo=UTC)

        with patch(
            "src.agent.domains.collector.tools.youtube_tool.get_transcript"
        ) as mock_get:
            mock_get.return_value = sample_transcript

            result = fetch_youtube(
                source_id="src_youtube",
                video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                video_title="Test Video",
                content_repo=mock_content_repo,
                published_at=published_at,
            )

            assert result is not None
            assert result.original_published_at == published_at

    def test_fetch_youtube_from_short_url(
        self,
        mock_content_repo: MagicMock,
        sample_transcript: YouTubeTranscript,
    ) -> None:
        """youtu.be 단축 URL 지원."""
        mock_content_repo.exists_by_content_key.return_value = False

        with patch(
            "src.agent.domains.collector.tools.youtube_tool.get_transcript"
        ) as mock_get:
            mock_get.return_value = sample_transcript

            result = fetch_youtube(
                source_id="src_youtube",
                video_url="https://youtu.be/dQw4w9WgXcQ",
                video_title="Short URL Video",
                content_repo=mock_content_repo,
            )

            assert result is not None
            mock_get.assert_called_once()
