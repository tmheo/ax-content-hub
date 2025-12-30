"""Tests for youtube_stt module.

YouTube 영상에서 음성 인식(STT)으로 자막을 추출하는 도구 테스트.
TDD: Red → Green → Refactor
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_settings() -> MagicMock:
    """Mock Settings fixture."""
    settings = MagicMock()
    settings.STT_ENABLED = True
    settings.STT_MODEL_SIZE = "small"
    settings.STT_COMPUTE_TYPE = "int8"
    settings.STT_MAX_VIDEO_DURATION_MINUTES = 30
    return settings


@pytest.fixture
def sample_audio_path(tmp_path: Path) -> Path:
    """임시 오디오 파일 경로."""
    audio_file = tmp_path / "test_audio.m4a"
    audio_file.write_bytes(b"fake audio content")
    return audio_file


# ============================================================================
# T030: TranscriptionResult dataclass 테스트
# ============================================================================


class TestTranscriptionResult:
    """TranscriptionResult dataclass 테스트."""

    def test_creation(self) -> None:
        """기본 생성."""
        from src.agent.domains.collector.tools.youtube_stt import TranscriptionResult

        result = TranscriptionResult(
            text="Hello, this is a test transcription.",
            language="en",
            language_probability=0.95,
            duration_seconds=120.5,
        )
        assert result.text == "Hello, this is a test transcription."
        assert result.language == "en"
        assert result.language_probability == 0.95
        assert result.duration_seconds == 120.5

    def test_immutable(self) -> None:
        """frozen=True 확인."""
        from src.agent.domains.collector.tools.youtube_stt import TranscriptionResult

        result = TranscriptionResult(
            text="Test",
            language="en",
            language_probability=0.9,
            duration_seconds=60.0,
        )
        with pytest.raises(AttributeError):
            result.text = "Modified"  # type: ignore[misc]


# ============================================================================
# T031: 예외 클래스 테스트
# ============================================================================


class TestExceptionClasses:
    """예외 클래스 테스트."""

    def test_youtube_extraction_error(self) -> None:
        """YouTubeExtractionError 생성."""
        from src.agent.domains.collector.tools.youtube_stt import YouTubeExtractionError

        error = YouTubeExtractionError("Failed to extract audio", video_id="abc123")
        assert "Failed to extract audio" in str(error)
        assert error.video_id == "abc123"

    def test_age_restricted_error(self) -> None:
        """AgeRestrictedError 생성."""
        from src.agent.domains.collector.tools.youtube_stt import AgeRestrictedError

        error = AgeRestrictedError("Video is age-restricted", video_id="xyz789")
        assert "age-restricted" in str(error).lower() or "Video is" in str(error)

    def test_video_unavailable_error(self) -> None:
        """VideoUnavailableError 생성."""
        from src.agent.domains.collector.tools.youtube_stt import VideoUnavailableError

        error = VideoUnavailableError("Video not found", video_id="notfound")
        assert error.video_id == "notfound"

    def test_transcription_error(self) -> None:
        """TranscriptionError 생성."""
        from src.agent.domains.collector.tools.youtube_stt import TranscriptionError

        error = TranscriptionError("Transcription failed")
        assert "Transcription failed" in str(error)


# ============================================================================
# T032: extract_audio() 테스트
# ============================================================================


class TestExtractAudio:
    """extract_audio() 테스트."""

    @pytest.mark.asyncio
    async def test_extract_audio_success(self, tmp_path: Path) -> None:
        """오디오 추출 성공."""
        from src.agent.domains.collector.tools.youtube_stt import extract_audio

        with patch(
            "src.agent.domains.collector.tools.youtube_stt.yt_dlp.YoutubeDL"
        ) as mock_ydl:
            # Mock yt-dlp
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.extract_info.return_value = {
                "duration": 600,  # 10분
                "title": "Test Video",
            }
            mock_ydl.return_value = mock_instance

            # 임시 파일 생성 시뮬레이션
            with patch("tempfile.mkdtemp", return_value=str(tmp_path)):
                audio_file = tmp_path / "abc123.m4a"
                audio_file.write_bytes(b"fake audio")

                result = await extract_audio(
                    video_id="abc123",
                    output_dir=str(tmp_path),
                )

            assert result is not None

    @pytest.mark.asyncio
    async def test_extract_audio_age_restricted(self) -> None:
        """연령 제한 영상 처리."""
        from src.agent.domains.collector.tools.youtube_stt import (
            AgeRestrictedError,
            extract_audio,
        )

        with patch(
            "src.agent.domains.collector.tools.youtube_stt.yt_dlp.YoutubeDL"
        ) as mock_ydl:
            import yt_dlp

            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.extract_info.side_effect = yt_dlp.utils.DownloadError(
                "Sign in to confirm your age"
            )
            mock_ydl.return_value = mock_instance

            with pytest.raises(AgeRestrictedError):
                await extract_audio(video_id="restricted123")

    @pytest.mark.asyncio
    async def test_extract_audio_video_unavailable(self) -> None:
        """영상 접근 불가 처리."""
        from src.agent.domains.collector.tools.youtube_stt import (
            VideoUnavailableError,
            extract_audio,
        )

        with patch(
            "src.agent.domains.collector.tools.youtube_stt.yt_dlp.YoutubeDL"
        ) as mock_ydl:
            import yt_dlp

            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.extract_info.side_effect = yt_dlp.utils.DownloadError(
                "Video unavailable"
            )
            mock_ydl.return_value = mock_instance

            with pytest.raises(VideoUnavailableError):
                await extract_audio(video_id="unavailable123")


# ============================================================================
# T033: transcribe_audio() 테스트
# ============================================================================


class TestTranscribeAudio:
    """transcribe_audio() 테스트."""

    @pytest.mark.asyncio
    async def test_transcribe_success(self, sample_audio_path: Path) -> None:
        """전사 성공."""
        from src.agent.domains.collector.tools.youtube_stt import transcribe_audio

        with patch(
            "src.agent.domains.collector.tools.youtube_stt.WhisperModel"
        ) as mock_whisper:
            # Mock faster-whisper
            mock_model = MagicMock()
            mock_segments = [
                MagicMock(text=" Hello world"),
                MagicMock(text=" This is a test"),
            ]
            mock_info = MagicMock()
            mock_info.language = "en"
            mock_info.language_probability = 0.95
            mock_info.duration = 120.0
            mock_model.transcribe.return_value = (iter(mock_segments), mock_info)
            mock_whisper.return_value = mock_model

            result = await transcribe_audio(
                audio_path=str(sample_audio_path),
                model_size="small",
                compute_type="int8",
            )

        assert result.text == "Hello world This is a test"
        assert result.language == "en"
        assert result.language_probability == 0.95

    @pytest.mark.asyncio
    async def test_transcribe_korean(self, sample_audio_path: Path) -> None:
        """한국어 전사."""
        from src.agent.domains.collector.tools.youtube_stt import transcribe_audio

        with patch(
            "src.agent.domains.collector.tools.youtube_stt.WhisperModel"
        ) as mock_whisper:
            mock_model = MagicMock()
            mock_segments = [
                MagicMock(text=" 안녕하세요"),
                MagicMock(text=" 테스트입니다"),
            ]
            mock_info = MagicMock()
            mock_info.language = "ko"
            mock_info.language_probability = 0.92
            mock_info.duration = 60.0
            mock_model.transcribe.return_value = (iter(mock_segments), mock_info)
            mock_whisper.return_value = mock_model

            result = await transcribe_audio(
                audio_path=str(sample_audio_path),
                model_size="small",
            )

        assert result.language == "ko"
        assert "안녕하세요" in result.text

    @pytest.mark.asyncio
    async def test_transcribe_error(self, sample_audio_path: Path) -> None:
        """전사 오류 처리."""
        from src.agent.domains.collector.tools.youtube_stt import (
            TranscriptionError,
            transcribe_audio,
        )

        with patch(
            "src.agent.domains.collector.tools.youtube_stt.WhisperModel"
        ) as mock_whisper:
            mock_whisper.side_effect = RuntimeError("Model loading failed")

            with pytest.raises(TranscriptionError):
                await transcribe_audio(
                    audio_path=str(sample_audio_path),
                    model_size="small",
                )


# ============================================================================
# T034: 영상 길이 제한 테스트
# ============================================================================


class TestVideoDurationLimit:
    """영상 길이 제한 테스트."""

    @pytest.mark.asyncio
    async def test_video_too_long(self, mock_settings: MagicMock) -> None:
        """영상 길이 초과."""
        from src.agent.domains.collector.tools.youtube_stt import (
            check_video_duration,
        )

        # 60분 영상 (30분 제한 초과)
        result = check_video_duration(
            duration_seconds=3600,  # 60분
            max_duration_minutes=30,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_video_within_limit(self, mock_settings: MagicMock) -> None:
        """영상 길이 제한 내."""
        from src.agent.domains.collector.tools.youtube_stt import (
            check_video_duration,
        )

        # 20분 영상 (30분 제한 이내)
        result = check_video_duration(
            duration_seconds=1200,  # 20분
            max_duration_minutes=30,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_video_exactly_at_limit(self, mock_settings: MagicMock) -> None:
        """영상 길이 정확히 제한값."""
        from src.agent.domains.collector.tools.youtube_stt import (
            check_video_duration,
        )

        result = check_video_duration(
            duration_seconds=1800,  # 30분
            max_duration_minutes=30,
        )
        assert result is True


# ============================================================================
# T035: 임시 파일 자동 삭제 테스트
# ============================================================================


class TestTempFileCleanup:
    """임시 파일 자동 삭제 테스트."""

    @pytest.mark.asyncio
    async def test_cleanup_on_success(self, tmp_path: Path) -> None:
        """성공 시 임시 파일 삭제."""
        from src.agent.domains.collector.tools.youtube_stt import cleanup_temp_files

        # 임시 파일 생성
        temp_file = tmp_path / "audio.m4a"
        temp_file.write_bytes(b"fake audio")
        assert temp_file.exists()

        cleanup_temp_files(str(temp_file))

        assert not temp_file.exists()

    @pytest.mark.asyncio
    async def test_cleanup_on_error(self, tmp_path: Path) -> None:
        """오류 시에도 임시 파일 삭제."""
        from src.agent.domains.collector.tools.youtube_stt import cleanup_temp_files

        # 임시 파일 생성
        temp_file = tmp_path / "audio.m4a"
        temp_file.write_bytes(b"fake audio")

        cleanup_temp_files(str(temp_file))

        assert not temp_file.exists()

    @pytest.mark.asyncio
    async def test_cleanup_missing_file(self) -> None:
        """존재하지 않는 파일 삭제 시도."""
        from src.agent.domains.collector.tools.youtube_stt import cleanup_temp_files

        # 존재하지 않는 파일 - 오류 없이 처리
        cleanup_temp_files("/nonexistent/file.m4a")
