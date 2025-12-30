"""Integration tests for YouTube STT fallback flow.

Firestore 에뮬레이터와 함께 YouTube STT 폴백 파이프라인을 테스트합니다.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.firestore_client import FirestoreClient
from src.agent.domains.collector.tools.youtube_stt import TranscriptionResult
from src.agent.domains.collector.tools.youtube_tool import (
    YouTubeTranscript,
    fetch_youtube,
)
from src.models.content import ProcessingStatus
from src.models.source import Source, SourceType
from src.repositories.content_repo import ContentRepository
from src.repositories.source_repo import SourceRepository
from tests.utils import is_emulator_available

# Firestore 에뮬레이터가 없으면 테스트 스킵
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not is_emulator_available(),
        reason="Firestore emulator not available at FIRESTORE_EMULATOR_HOST",
    ),
]


class TestYouTubeSTTFlowIntegration:
    """YouTube STT 폴백 플로우 통합 테스트."""

    @pytest.fixture
    def unique_project(self) -> str:
        """테스트별 고유 프로젝트 ID."""
        return f"test-project-{uuid.uuid4().hex[:8]}"

    @pytest.fixture
    def firestore_client(self, unique_project: str) -> FirestoreClient:
        """실제 Firestore 에뮬레이터 클라이언트 (테스트별 격리)."""
        return FirestoreClient(project_id=unique_project)

    @pytest.fixture
    def source_repo(self, firestore_client: FirestoreClient) -> SourceRepository:
        """SourceRepository with real Firestore."""
        return SourceRepository(firestore_client)

    @pytest.fixture
    def content_repo(self, firestore_client: FirestoreClient) -> ContentRepository:
        """ContentRepository with real Firestore."""
        return ContentRepository(firestore_client)

    @pytest.fixture
    def test_source_id(self) -> str:
        """테스트용 소스 ID."""
        return f"src_test_{uuid.uuid4().hex[:8]}"

    @pytest.fixture
    def test_youtube_source(
        self, source_repo: SourceRepository, test_source_id: str
    ) -> Source:
        """테스트용 YouTube 소스 생성."""
        now = datetime.now(UTC)
        source_url = "https://www.youtube.com/@anthropic-ai"

        # Firestore에 직접 저장
        source_repo._db.set(
            source_repo.collection_name,
            test_source_id,
            {
                "id": test_source_id,
                "name": "Anthropic AI Channel",
                "type": "youtube",
                "url": source_url,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
                "config": {},
                "language": "en",
                "fetch_error_count": 0,
            },
        )

        return Source(
            id=test_source_id,
            name="Anthropic AI Channel",
            type=SourceType.YOUTUBE,
            url=source_url,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    def test_youtube_with_transcript_saves_to_firestore(
        self,
        test_youtube_source: Source,
        content_repo: ContentRepository,
    ) -> None:
        """자막이 있는 YouTube 영상이 Firestore에 저장되는지 확인."""
        mock_transcript = YouTubeTranscript(
            video_id="dQw4w9WgXcQ",
            text="This is a test transcript from YouTube captions. "
            "Claude is an AI assistant made by Anthropic.",
            language="en",
            duration_seconds=180.5,
        )

        with patch(
            "src.agent.domains.collector.tools.youtube_tool.get_transcript",
            return_value=mock_transcript,
        ):
            result = fetch_youtube(
                source_id=test_youtube_source.id,
                video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                video_title="Test Video with Captions",
                content_repo=content_repo,
            )

            # 콘텐츠가 생성되었는지 확인
            assert result is not None
            assert result.source_id == test_youtube_source.id
            assert result.original_title == "Test Video with Captions"
            assert result.original_body == mock_transcript.text
            assert result.original_language == "en"
            assert result.processing_status == ProcessingStatus.PENDING

            # Firestore에서 조회
            saved = content_repo.get_by_id(result.id)
            assert saved is not None
            assert "youtube.com" in saved.original_url

    def test_youtube_stt_fallback_when_no_transcript(
        self,
        test_youtube_source: Source,
        content_repo: ContentRepository,
    ) -> None:
        """자막이 없을 때 STT 폴백이 동작하는지 확인."""
        mock_stt_result = TranscriptionResult(
            text="This is transcribed text from STT. "
            "The audio was processed using Whisper model.",
            language="en",
            language_probability=0.98,
            duration_seconds=120.0,
        )

        with (
            patch(
                "src.agent.domains.collector.tools.youtube_tool.get_transcript",
                return_value=None,  # 자막 없음
            ),
            patch(
                "src.agent.domains.collector.tools.youtube_tool.get_settings"
            ) as mock_settings,
            patch(
                "src.agent.domains.collector.tools.youtube_tool.fetch_youtube_with_stt",
                new_callable=AsyncMock,
                return_value=mock_stt_result,
            ),
        ):
            # STT 활성화
            mock_settings.return_value = MagicMock(STT_ENABLED=True)

            result = fetch_youtube(
                source_id=test_youtube_source.id,
                video_url="https://www.youtube.com/watch?v=abc123xyz99",
                video_title="Test Video without Captions",
                content_repo=content_repo,
            )

            # STT 폴백으로 콘텐츠 생성 확인
            assert result is not None
            assert result.original_body == mock_stt_result.text
            assert result.original_language == "en"

    def test_youtube_deduplication(
        self,
        test_youtube_source: Source,
        content_repo: ContentRepository,
    ) -> None:
        """중복 YouTube 영상은 다시 수집되지 않는지 확인."""
        mock_transcript = YouTubeTranscript(
            video_id="unique123abc",
            text="Unique video transcript content.",
            language="en",
            duration_seconds=60.0,
        )

        with patch(
            "src.agent.domains.collector.tools.youtube_tool.get_transcript",
            return_value=mock_transcript,
        ):
            # 첫 번째 수집
            first_result = fetch_youtube(
                source_id=test_youtube_source.id,
                video_url="https://www.youtube.com/watch?v=unique123abc",
                video_title="Unique Video",
                content_repo=content_repo,
            )
            assert first_result is not None

            # 두 번째 수집 (동일 video ID)
            second_result = fetch_youtube(
                source_id=test_youtube_source.id,
                video_url="https://www.youtube.com/watch?v=unique123abc",
                video_title="Unique Video",
                content_repo=content_repo,
            )

            # 중복이므로 None 반환
            assert second_result is None

            # Firestore에는 하나만 존재
            all_contents = content_repo.find_by_source(test_youtube_source.id)
            assert len(all_contents) == 1

    def test_youtube_returns_none_when_no_transcript_and_stt_disabled(
        self,
        test_youtube_source: Source,
        content_repo: ContentRepository,
    ) -> None:
        """자막 없고 STT 비활성화 시 None 반환 확인."""
        with (
            patch(
                "src.agent.domains.collector.tools.youtube_tool.get_transcript",
                return_value=None,
            ),
            patch(
                "src.agent.domains.collector.tools.youtube_tool.get_settings"
            ) as mock_settings,
        ):
            # STT 비활성화
            mock_settings.return_value = MagicMock(STT_ENABLED=False)

            result = fetch_youtube(
                source_id=test_youtube_source.id,
                video_url="https://www.youtube.com/watch?v=nosttstt123",
                video_title="Video without STT",
                content_repo=content_repo,
            )

            # 자막도 없고 STT도 비활성화되어 None 반환
            assert result is None

    def test_youtube_url_normalization(
        self,
        test_youtube_source: Source,
        content_repo: ContentRepository,
    ) -> None:
        """다양한 YouTube URL 형식이 정규화되는지 확인."""
        mock_transcript = YouTubeTranscript(
            video_id="testVideo123",
            text="Test content for URL normalization.",
            language="en",
            duration_seconds=90.0,
        )

        with patch(
            "src.agent.domains.collector.tools.youtube_tool.get_transcript",
            return_value=mock_transcript,
        ):
            # youtu.be 형식으로 수집
            result = fetch_youtube(
                source_id=test_youtube_source.id,
                video_url="https://youtu.be/testVideo123",
                video_title="URL Test Video",
                content_repo=content_repo,
            )

            assert result is not None
            # 정규화된 URL 확인
            assert result.original_url == "https://www.youtube.com/watch?v=testVideo123"

    def test_youtube_korean_transcript(
        self,
        test_youtube_source: Source,
        content_repo: ContentRepository,
    ) -> None:
        """한국어 자막 수집 확인."""
        mock_transcript = YouTubeTranscript(
            video_id="koreanVid123",
            text="안녕하세요. 이것은 한국어 자막 테스트입니다. "
            "Claude는 Anthropic에서 만든 AI 어시스턴트입니다.",
            language="ko",
            duration_seconds=150.0,
        )

        with patch(
            "src.agent.domains.collector.tools.youtube_tool.get_transcript",
            return_value=mock_transcript,
        ):
            result = fetch_youtube(
                source_id=test_youtube_source.id,
                video_url="https://www.youtube.com/watch?v=koreanVid123",
                video_title="한국어 테스트 영상",
                content_repo=content_repo,
                languages=["ko", "en"],
            )

            assert result is not None
            assert result.original_language == "ko"
            assert "한국어" in result.original_body
