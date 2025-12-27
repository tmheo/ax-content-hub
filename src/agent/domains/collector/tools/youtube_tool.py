"""YouTube transcript collection tool.

youtube-transcript-api를 사용하여 YouTube 자막을 수집합니다.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import feedparser
import httpx
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


def is_channel_url(url: str) -> bool:
    """YouTube URL이 채널 URL인지 확인.

    Args:
        url: YouTube URL.

    Returns:
        채널 URL이면 True, 아니면 False.
    """
    if not url:
        return False

    parsed = urlparse(url)

    # youtube.com 도메인 확인
    if "youtube.com" not in parsed.netloc:
        return False

    path = parsed.path

    # 채널 URL 패턴들
    # /@handle, /channel/UC..., /c/channelname, /user/username
    if path.startswith("/@"):
        return True
    if path.startswith("/channel/"):
        return True
    if path.startswith("/c/"):
        return True
    if path.startswith("/user/"):
        return True

    return False


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
        # 인스턴스 생성 후 fetch 호출 (새 API)
        api = YouTubeTranscriptApi()
        transcript_list = api.fetch(video_id, languages=languages)

        # 텍스트 연결 (새 API는 FetchedTranscriptSnippet 객체 리스트 반환)
        text_parts = [segment.text for segment in transcript_list]
        full_text = " ".join(text_parts)

        # 전체 길이 계산 (마지막 세그먼트의 시작 + 지속시간)
        duration = 0.0
        if transcript_list:
            last_segment = transcript_list[-1]
            duration = last_segment.start + last_segment.duration

        # 실제 사용된 언어 확인
        actual_language = languages[0]
        if hasattr(transcript_list, "language"):
            actual_language = transcript_list.language

        return YouTubeTranscript(
            video_id=video_id,
            text=full_text,
            language=actual_language,
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


def get_channel_id(channel_url: str) -> str | None:
    """YouTube 채널 URL에서 channel ID 추출.

    @handle 형식의 URL에서 실제 channel ID를 가져옵니다.

    Args:
        channel_url: YouTube 채널 URL (예: https://www.youtube.com/@anthropic-ai)

    Returns:
        channel ID 또는 None.
    """
    parsed = urlparse(channel_url)

    # 이미 channel ID 형식인 경우 (UC로 시작하는 24자)
    if "/channel/" in parsed.path:
        parts = parsed.path.split("/channel/")
        if len(parts) > 1:
            channel_id = parts[1].split("/")[0]
            if channel_id.startswith("UC") and len(channel_id) == 24:
                return channel_id

    # @handle 형식인 경우 HTML에서 channel ID 추출
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(channel_url)
            response.raise_for_status()

            # HTML에서 channel ID 추출
            # 패턴: "channelId":"UC..."
            match = re.search(r'"channelId":"(UC[a-zA-Z0-9_-]{22})"', response.text)
            if match:
                return match.group(1)

            # 대체 패턴: /channel/UC... 형태의 canonical URL
            match = re.search(
                r'<link rel="canonical" href="[^"]*?/channel/(UC[a-zA-Z0-9_-]{22})"',
                response.text,
            )
            if match:
                return match.group(1)

    except Exception:
        pass

    return None


def fetch_channel_videos(
    source_id: str,
    channel_url: str,
    content_repo: ContentRepository,
    max_videos: int = 10,
) -> list[Content]:
    """YouTube 채널에서 최신 영상들을 수집.

    채널의 RSS 피드를 사용하여 최신 영상 목록을 가져오고,
    각 영상의 자막을 수집합니다.

    Args:
        source_id: 소스 ID.
        channel_url: YouTube 채널 URL.
        content_repo: ContentRepository 인스턴스.
        max_videos: 최대 수집 영상 수 (기본 10).

    Returns:
        수집된 Content 목록.
    """
    # 채널 ID 추출
    channel_id = get_channel_id(channel_url)
    if not channel_id:
        return []

    # RSS 피드 URL
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    try:
        feed = feedparser.parse(feed_url)
    except Exception:
        return []

    if not feed.entries:
        return []

    collected: list[Content] = []

    for entry in feed.entries[:max_videos]:
        video_url = entry.get("link", "")
        video_title = entry.get("title", "")
        published_str = entry.get("published", "")

        if not video_url or not video_title:
            continue

        # 발행일 파싱
        published_at = None
        if published_str:
            try:
                from email.utils import parsedate_to_datetime

                published_at = parsedate_to_datetime(published_str)
            except Exception:
                pass

        # 자막 수집
        content = fetch_youtube(
            source_id=source_id,
            video_url=video_url,
            video_title=video_title,
            content_repo=content_repo,
            published_at=published_at,
        )

        if content:
            collected.append(content)

    return collected
