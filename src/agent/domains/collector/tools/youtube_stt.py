"""YouTube STT (Speech-to-Text) tool.

자막이 없는 YouTube 영상에서 음성 인식으로 텍스트를 추출합니다.
yt-dlp로 오디오 추출 후 faster-whisper로 전사합니다.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import structlog
import yt_dlp
from faster_whisper import WhisperModel

from src.config.settings import get_settings

logger = structlog.get_logger(__name__)


# ============================================================================
# T037: 예외 클래스
# ============================================================================


class YouTubeExtractionError(Exception):
    """YouTube 오디오 추출 실패 예외."""

    def __init__(self, message: str, video_id: str | None = None) -> None:
        self.video_id = video_id
        super().__init__(f"{message} (video_id={video_id})" if video_id else message)


class AgeRestrictedError(YouTubeExtractionError):
    """연령 제한 영상 예외."""

    pass


class VideoUnavailableError(YouTubeExtractionError):
    """영상 접근 불가 예외."""

    pass


class TranscriptionError(Exception):
    """음성 인식 실패 예외."""

    pass


# ============================================================================
# T036: TranscriptionResult dataclass
# ============================================================================


@dataclass(frozen=True)
class TranscriptionResult:
    """음성 인식 결과."""

    text: str
    """전사된 텍스트"""

    language: str
    """감지된 언어 코드"""

    language_probability: float
    """언어 감지 확률 (0.0-1.0)"""

    duration_seconds: float
    """오디오 길이 (초)"""


# ============================================================================
# T040: 영상 길이 확인 함수
# ============================================================================


def check_video_duration(
    duration_seconds: float,
    max_duration_minutes: int,
) -> bool:
    """영상 길이가 제한 내인지 확인.

    Args:
        duration_seconds: 영상 길이 (초)
        max_duration_minutes: 최대 허용 길이 (분)

    Returns:
        제한 내이면 True, 초과면 False
    """
    max_seconds = max_duration_minutes * 60
    return duration_seconds <= max_seconds


# ============================================================================
# T041: 임시 파일 정리 함수
# ============================================================================


def cleanup_temp_files(file_path: str) -> None:
    """임시 파일 삭제.

    Args:
        file_path: 삭제할 파일 경로
    """
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.debug("temp_file_deleted", path=file_path)
    except OSError as e:
        logger.warning("temp_file_cleanup_failed", path=file_path, error=str(e))


# ============================================================================
# T038: extract_audio() - yt-dlp로 오디오 추출
# ============================================================================


async def extract_audio(
    video_id: str,
    output_dir: str | None = None,
) -> tuple[str, float]:
    """YouTube 영상에서 오디오 추출.

    Args:
        video_id: YouTube 영상 ID (11자)
        output_dir: 출력 디렉토리 (없으면 임시 디렉토리 사용)

    Returns:
        (오디오 파일 경로, 영상 길이(초)) 튜플

    Raises:
        AgeRestrictedError: 연령 제한 영상
        VideoUnavailableError: 영상 접근 불가
        YouTubeExtractionError: 기타 추출 오류
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="ax_stt_")

    output_template = os.path.join(output_dir, f"{video_id}.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)

            if info is None:
                raise YouTubeExtractionError("Failed to get video info", video_id)

            duration = info.get("duration", 0)
            audio_path = os.path.join(output_dir, f"{video_id}.m4a")

            if not os.path.exists(audio_path):
                # 확장자가 다를 수 있음
                for ext in ["m4a", "mp3", "opus", "webm"]:
                    alt_path = os.path.join(output_dir, f"{video_id}.{ext}")
                    if os.path.exists(alt_path):
                        audio_path = alt_path
                        break

            logger.info(
                "audio_extracted",
                video_id=video_id,
                duration=duration,
                path=audio_path,
            )

            return audio_path, float(duration)

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()

        if "age" in error_msg or "sign in" in error_msg:
            raise AgeRestrictedError(str(e), video_id) from e
        elif "unavailable" in error_msg or "private" in error_msg:
            raise VideoUnavailableError(str(e), video_id) from e
        else:
            raise YouTubeExtractionError(str(e), video_id) from e

    except Exception as e:
        raise YouTubeExtractionError(str(e), video_id) from e


# ============================================================================
# T039: transcribe_audio() - faster-whisper로 전사
# ============================================================================


async def transcribe_audio(
    audio_path: str,
    model_size: str = "small",
    compute_type: str = "int8",
) -> TranscriptionResult:
    """오디오 파일 전사.

    Args:
        audio_path: 오디오 파일 경로
        model_size: Whisper 모델 크기 (tiny, base, small, medium)
        compute_type: 연산 타입 (int8, float16, float32)

    Returns:
        TranscriptionResult 전사 결과

    Raises:
        TranscriptionError: 전사 실패
    """
    try:
        model = WhisperModel(
            model_size,
            device="cpu",
            compute_type=compute_type,
        )

        segments, info = model.transcribe(
            audio_path,
            beam_size=5,
            vad_filter=True,  # VAD로 무음 구간 스킵
        )

        # 세그먼트에서 텍스트 추출
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

        full_text = " ".join(text_parts)

        logger.info(
            "audio_transcribed",
            language=info.language,
            probability=info.language_probability,
            duration=info.duration,
            text_length=len(full_text),
        )

        return TranscriptionResult(
            text=full_text,
            language=info.language,
            language_probability=info.language_probability,
            duration_seconds=info.duration,
        )

    except Exception as e:
        logger.error("transcription_failed", error=str(e))
        raise TranscriptionError(str(e)) from e


# ============================================================================
# 통합 함수: fetch_youtube_with_stt
# ============================================================================


async def fetch_youtube_with_stt(
    video_id: str,
    max_duration_minutes: int | None = None,
) -> TranscriptionResult | None:
    """YouTube 영상에서 STT로 텍스트 추출.

    Args:
        video_id: YouTube 영상 ID
        max_duration_minutes: 최대 영상 길이 (None이면 설정값 사용)

    Returns:
        TranscriptionResult 또는 None (건너뜀)

    Raises:
        YouTubeExtractionError: 오디오 추출 실패
        TranscriptionError: 음성 인식 실패
    """
    settings = get_settings()

    if not settings.STT_ENABLED:
        logger.info("stt_disabled", video_id=video_id)
        return None

    if max_duration_minutes is None:
        max_duration_minutes = settings.STT_MAX_VIDEO_DURATION_MINUTES

    audio_path: str | None = None

    try:
        # 1. 오디오 추출
        audio_path, duration = await extract_audio(video_id)

        # 2. 영상 길이 확인
        if not check_video_duration(duration, max_duration_minutes):
            logger.info(
                "video_too_long_for_stt",
                video_id=video_id,
                duration_minutes=duration / 60,
                max_minutes=max_duration_minutes,
            )
            return None

        # 3. 전사
        result = await transcribe_audio(
            audio_path=audio_path,
            model_size=settings.STT_MODEL_SIZE,
            compute_type=settings.STT_COMPUTE_TYPE,
        )

        return result

    finally:
        # 4. 임시 파일 정리
        if audio_path:
            cleanup_temp_files(audio_path)
