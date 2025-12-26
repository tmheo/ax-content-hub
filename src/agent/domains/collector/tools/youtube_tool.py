"""YouTube transcript collection tool.

youtube-transcript-api를 사용하여 YouTube 자막을 수집합니다.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from src.models.content import Content, ProcessingStatus, generate_content_key
from src.repositories.content_repo import ContentRepository


@dataclass
class YouTubeTranscript:
    """YouTube 자막 데이터."""

    video_id: str
    text: str
    language: str
    duration_seconds: float


def extract_video_id(url_or_id: str) -> str | None:
    """YouTube URL 또는 ID에서 video ID 추출.

    Args:
        url_or_id: YouTube URL 또는 video ID.

    Returns:
        video ID 또는 None.
    """
    if not url_or_id:
        return None

    # 11자리 video ID 패턴 (YouTube video ID는 11자)
    video_id_pattern = r"^[a-zA-Z0-9_-]{11}$"

    # 이미 video ID인 경우
    if re.match(video_id_pattern, url_or_id):
        return url_or_id

    # URL 파싱
    parsed = urlparse(url_or_id)

    # youtube.com/watch?v=VIDEO_ID
    if "youtube.com" in parsed.netloc:
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            video_ids = qs.get("v")
            if video_ids:
                return video_ids[0]

        # youtube.com/embed/VIDEO_ID
        if parsed.path.startswith("/embed/"):
            return parsed.path.split("/")[2]

        # youtube.com/shorts/VIDEO_ID
        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/")[2]

    # youtu.be/VIDEO_ID
    if "youtu.be" in parsed.netloc:
        return parsed.path.lstrip("/").split("?")[0]

    return None


def get_transcript(
    video_id: str,
    languages: list[str] | None = None,
) -> YouTubeTranscript | None:
    """YouTube 자막 가져오기.

    Args:
        video_id: YouTube video ID.
        languages: 선호 언어 목록 (기본: ["en"]).

    Returns:
        자막 데이터 또는 None.
    """
    if languages is None:
        languages = ["en"]

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(
            video_id, languages=languages
        )

        # 텍스트 연결
        text_parts = [segment["text"] for segment in transcript_list]
        full_text = " ".join(text_parts)

        # 전체 길이 계산 (마지막 세그먼트의 시작 + 지속시간)
        duration = 0.0
        if transcript_list:
            last_segment = transcript_list[-1]
            duration = last_segment["start"] + last_segment["duration"]

        return YouTubeTranscript(
            video_id=video_id,
            text=full_text,
            language=languages[0],  # 첫 번째 요청 언어
            duration_seconds=duration,
        )

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return None
    except Exception:
        return None


def fetch_youtube(
    source_id: str,
    video_url: str,
    video_title: str,
    content_repo: ContentRepository,
    published_at: datetime | None = None,
    languages: list[str] | None = None,
) -> Content | None:
    """YouTube 영상에서 자막 수집.

    중복 콘텐츠(content_key 기준)는 건너뜁니다.

    Args:
        source_id: 소스 ID.
        video_url: YouTube 영상 URL.
        video_title: 영상 제목.
        content_repo: ContentRepository 인스턴스.
        published_at: 발행일.
        languages: 선호 언어 목록.

    Returns:
        새로 수집된 Content 또는 None.

    Raises:
        ValueError: 잘못된 YouTube URL.
    """
    # Video ID 추출
    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError(f"Invalid YouTube URL: {video_url}")

    # 정규화된 YouTube URL 생성
    normalized_url = f"https://www.youtube.com/watch?v={video_id}"

    # content_key 생성 (URL 정규화 포함)
    content_key = generate_content_key(source_id, normalized_url)

    # 중복 체크
    if content_repo.exists_by_content_key(content_key):
        return None

    # 자막 가져오기
    if languages is None:
        languages = ["en", "ko"]  # 기본값: 영어, 한국어

    transcript = get_transcript(video_id, languages=languages)
    if transcript is None:
        return None

    # 새 Content 생성
    now = datetime.now(UTC)
    content = Content(
        id=f"cnt_{uuid.uuid4().hex[:12]}",
        source_id=source_id,
        content_key=content_key,
        original_url=normalized_url,
        original_title=video_title,
        original_body=transcript.text,
        original_language=transcript.language,
        original_published_at=published_at,
        processing_status=ProcessingStatus.PENDING,
        collected_at=now,
    )

    # Firestore에 저장
    content_repo.create(content)

    return content
