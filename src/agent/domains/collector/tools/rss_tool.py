"""RSS feed collection tool.

feedparser를 사용하여 RSS 피드에서 콘텐츠를 수집합니다.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import feedparser

from src.models.content import Content, ProcessingStatus, generate_content_key
from src.repositories.content_repo import ContentRepository


@dataclass
class RSSEntry:
    """파싱된 RSS 엔트리."""

    title: str
    url: str
    body: str | None
    published_at: datetime | None


def parse_rss_feed(
    feed_url: str,
    limit: int = 20,
) -> list[RSSEntry]:
    """RSS 피드 파싱.

    Args:
        feed_url: RSS 피드 URL.
        limit: 최대 엔트리 수.

    Returns:
        파싱된 엔트리 목록.

    Raises:
        ValueError: 피드 파싱 실패.
    """
    feed = feedparser.parse(feed_url)

    # 피드 파싱 에러 체크
    if feed.bozo and not feed.entries:
        raise ValueError(f"Failed to parse RSS feed: {feed.bozo_exception}")

    entries: list[RSSEntry] = []

    for entry in feed.entries[:limit]:
        # 제목과 링크는 필수
        title = entry.get("title", "").strip()
        url = entry.get("link", "").strip()

        if not title or not url:
            continue

        # 본문: content > summary > description
        body = None
        content_list = entry.get("content")
        if content_list:
            body = (
                content_list[0].get("value", "")
                if isinstance(content_list, list)
                else None
            )
        if not body:
            body = entry.get("summary") or entry.get("description")

        # 발행일 파싱
        published_at = None
        published_parsed = entry.get("published_parsed")
        if published_parsed:
            try:
                published_at = datetime(
                    year=published_parsed[0],
                    month=published_parsed[1],
                    day=published_parsed[2],
                    hour=published_parsed[3],
                    minute=published_parsed[4],
                    second=published_parsed[5],
                    tzinfo=UTC,
                )
            except (TypeError, ValueError, IndexError):
                pass

        entries.append(
            RSSEntry(
                title=title,
                url=url,
                body=body,
                published_at=published_at,
            )
        )

    return entries


def fetch_rss(
    source_id: str,
    source_url: str,
    content_repo: ContentRepository,
    limit: int = 20,
) -> list[Content]:
    """RSS 피드에서 새 콘텐츠 수집.

    중복 콘텐츠(content_key 기준)는 건너뜁니다.

    Args:
        source_id: 소스 ID.
        source_url: RSS 피드 URL.
        content_repo: ContentRepository 인스턴스.
        limit: 최대 수집 수.

    Returns:
        새로 수집된 Content 목록.

    Raises:
        ValueError: 피드 파싱 실패.
    """
    entries = parse_rss_feed(source_url, limit=limit)
    new_contents: list[Content] = []
    now = datetime.now(UTC)

    for entry in entries:
        # content_key 생성 (URL 정규화 포함)
        content_key = generate_content_key(source_id, entry.url)

        # 중복 체크
        if content_repo.exists_by_content_key(content_key):
            continue

        # 새 Content 생성
        content = Content(
            id=f"cnt_{uuid.uuid4().hex[:12]}",
            source_id=source_id,
            content_key=content_key,
            original_url=entry.url,
            original_title=entry.title,
            original_body=entry.body,
            original_language="en",  # 기본값, 나중에 감지 가능
            original_published_at=entry.published_at,
            processing_status=ProcessingStatus.PENDING,
            collected_at=now,
        )

        # Firestore에 저장
        content_repo.create(content)
        new_contents.append(content)

    return new_contents
