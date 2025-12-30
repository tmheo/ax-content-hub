"""Web scraper tool with 4-stage fallback strategy.

RSS가 없는 웹사이트에서 콘텐츠를 수집하는 도구입니다.
4단계 폴백 전략: Static → Dynamic → Structural → URL Pattern
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

import httpx
import structlog
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from src.config.settings import get_settings
from src.models.content import Content, ProcessingStatus

if TYPE_CHECKING:
    from src.repositories.content_repo import ContentRepository

logger = structlog.get_logger(__name__)


# ============================================================================
# T025: 예외 클래스
# ============================================================================


class ScrapingError(Exception):
    """웹 스크래핑 실패 예외."""

    def __init__(self, message: str, url: str | None = None) -> None:
        self.url = url
        super().__init__(f"{message} (url={url})" if url else message)


class NetworkError(ScrapingError):
    """네트워크 오류 예외."""

    pass


class ScrapingTimeoutError(ScrapingError):
    """타임아웃 예외."""

    pass


# ============================================================================
# T018: WebScraperConfig dataclass
# ============================================================================


@dataclass(frozen=True)
class WebScraperConfig:
    """웹 스크래핑 설정."""

    selector: str | None = None
    """콘텐츠 추출 CSS selector"""

    wait_for: str | None = None
    """JS 로딩 대기 selector"""

    url_pattern: str | None = None
    """콘텐츠 URL 패턴 (정규식) - Stage 4용"""

    timeout_seconds: int = 30
    """페이지별 타임아웃 (초)"""

    post_link_pattern: str | None = None
    """목록 페이지에서 포스트 링크를 추출하는 정규식.

    설정되면 목록 모드로 동작:
    1. 목록 페이지에서 패턴에 매칭되는 링크 추출
    2. 각 링크에서 개별 포스트 수집

    예: r"^/blog/[a-z0-9-]+$" (claude.com/blog용)
    """

    max_posts: int = 10
    """목록 모드에서 최대 수집 포스트 수"""

    use_playwright_for_listing: bool = False
    """목록 페이지에서 JavaScript 렌더링이 필요한 경우 True"""

    @classmethod
    def from_source_config(cls, config: dict) -> WebScraperConfig:
        """Source.config에서 생성."""
        return cls(
            selector=config.get("selector"),
            wait_for=config.get("wait_for"),
            url_pattern=config.get("url_pattern"),
            timeout_seconds=config.get("timeout_seconds", 30),
            post_link_pattern=config.get("post_link_pattern"),
            max_posts=config.get("max_posts", 10),
            use_playwright_for_listing=config.get("use_playwright_for_listing", False),
        )


# ============================================================================
# T019: ScrapedContent dataclass
# ============================================================================


@dataclass(frozen=True)
class ScrapedContent:
    """스크래핑된 콘텐츠 결과."""

    url: str
    """콘텐츠 URL"""

    title: str
    """콘텐츠 제목"""

    body: str
    """콘텐츠 본문"""

    published_at: datetime | None = None
    """발행일 (파싱 가능한 경우)"""

    extraction_stage: int = 0
    """추출된 폴백 단계 (1-4)"""

    def is_valid(self, min_body_length: int = 200) -> bool:
        """유효한 콘텐츠인지 확인."""
        return bool(self.title) and len(self.body) >= min_body_length


# ============================================================================
# Cloud Run 최적화 브라우저 인자
# ============================================================================

BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--single-process",
    "--js-flags=--max-old-space-size=512",
]


# ============================================================================
# T020: Stage 1 - Static HTML 추출
# ============================================================================


async def _extract_stage1_static(
    url: str,
    config: WebScraperConfig,
) -> ScrapedContent | None:
    """Stage 1: Static HTML 추출 (httpx + BeautifulSoup).

    Args:
        url: 수집할 URL
        config: 스크래핑 설정

    Returns:
        ScrapedContent 또는 None (실패 시)
    """
    settings = get_settings()

    try:
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; AXContentBot/1.0)",
                },
                follow_redirects=True,
            )
            response.raise_for_status()
            html = response.text

        soup = BeautifulSoup(html, "lxml")

        # selector가 있으면 해당 요소에서 추출
        if config.selector:
            element = soup.select_one(config.selector)
            if not element:
                logger.debug("selector_not_found", selector=config.selector, url=url)
                return None
            title = _extract_title(element) or _extract_title(soup)
            body = element.get_text(separator=" ", strip=True)
        else:
            # 기본 추출
            title = _extract_title(soup)
            body = _extract_body_text(soup)

        if not title:
            title = soup.title.string if soup.title else ""

        # 콘텐츠 길이 검증
        if len(body) < settings.SCRAPING_MIN_CONTENT_LENGTH:
            logger.debug(
                "content_too_short",
                url=url,
                length=len(body),
                min_length=settings.SCRAPING_MIN_CONTENT_LENGTH,
            )
            return None

        published_at = _extract_published_date(soup)

        return ScrapedContent(
            url=url,
            title=title.strip() if title else "",
            body=body,
            published_at=published_at,
            extraction_stage=1,
        )

    except httpx.HTTPStatusError as e:
        logger.warning("http_error", url=url, status=e.response.status_code)
        return None
    except Exception as e:
        logger.warning("stage1_extraction_failed", url=url, error=str(e))
        return None


# ============================================================================
# T021: Stage 2 - Dynamic JS 추출
# ============================================================================


async def _extract_stage2_dynamic(
    url: str,
    config: WebScraperConfig,
) -> ScrapedContent | None:
    """Stage 2: Dynamic JS 추출 (Playwright + CSS selector).

    Args:
        url: 수집할 URL
        config: 스크래핑 설정

    Returns:
        ScrapedContent 또는 None (실패 시)
    """
    settings = get_settings()

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=BROWSER_ARGS,
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (compatible; AXContentBot/1.0)",
            )
            page = await context.new_page()

            try:
                await page.goto(url, timeout=config.timeout_seconds * 1000)

                # wait_for selector가 있으면 대기
                if config.wait_for:
                    await page.wait_for_selector(
                        config.wait_for,
                        timeout=config.timeout_seconds * 1000,
                    )

                html = await page.content()
            finally:
                await browser.close()

        soup = BeautifulSoup(html, "lxml")

        # selector가 있으면 해당 요소에서 추출
        if config.selector:
            element = soup.select_one(config.selector)
            if not element:
                logger.debug("selector_not_found", selector=config.selector, url=url)
                return None
            title = _extract_title(element) or _extract_title(soup)
            body = element.get_text(separator=" ", strip=True)
        else:
            title = _extract_title(soup)
            body = _extract_body_text(soup)

        if not title:
            title = soup.title.string if soup.title else ""

        # 콘텐츠 길이 검증
        if len(body) < settings.SCRAPING_MIN_CONTENT_LENGTH:
            return None

        return ScrapedContent(
            url=url,
            title=title.strip() if title else "",
            body=body,
            published_at=_extract_published_date(soup),
            extraction_stage=2,
        )

    except Exception as e:
        logger.warning("stage2_extraction_failed", url=url, error=str(e))
        return None


# ============================================================================
# T022: Stage 3 - Structural 추출
# ============================================================================


async def _extract_stage3_structural(url: str) -> ScrapedContent | None:
    """Stage 3: Structural 추출 (DOM 휴리스틱).

    main, article, section 등 시맨틱 태그에서 콘텐츠 추출.

    Args:
        url: 수집할 URL

    Returns:
        ScrapedContent 또는 None (실패 시)
    """
    settings = get_settings()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AXContentBot/1.0)"},
                follow_redirects=True,
            )
            response.raise_for_status()
            html = response.text

        soup = BeautifulSoup(html, "lxml")

        # 시맨틱 태그 우선순위
        content_elements = ["main", "article", "[role='main']", ".content", "#content"]

        for selector in content_elements:
            element = soup.select_one(selector)
            if element:
                body = element.get_text(separator=" ", strip=True)
                if len(body) >= settings.SCRAPING_MIN_CONTENT_LENGTH:
                    title = _extract_title(element) or _extract_title(soup)
                    if not title:
                        title = soup.title.string if soup.title else ""

                    return ScrapedContent(
                        url=url,
                        title=title.strip() if title else "",
                        body=body,
                        published_at=_extract_published_date(soup),
                        extraction_stage=3,
                    )

        return None

    except Exception as e:
        logger.warning("stage3_extraction_failed", url=url, error=str(e))
        return None


# ============================================================================
# T023: Stage 4 - URL Pattern 추출
# ============================================================================


async def _extract_stage4_url_pattern(
    url: str,
    config: WebScraperConfig,
) -> list[str]:
    """Stage 4: URL Pattern 추출 (링크 분석).

    페이지의 링크 중 패턴에 매칭되는 URL 목록 반환.

    Args:
        url: 수집할 URL
        config: 스크래핑 설정

    Returns:
        매칭된 URL 목록
    """
    if not config.url_pattern:
        return []

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AXContentBot/1.0)"},
                follow_redirects=True,
            )
            response.raise_for_status()
            html = response.text

        soup = BeautifulSoup(html, "lxml")
        pattern = re.compile(config.url_pattern)

        matched_urls: list[str] = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            # 상대 경로를 절대 경로로 변환
            full_url = urljoin(url, href)

            if pattern.search(full_url):
                matched_urls.append(full_url)

        # 중복 제거
        return list(dict.fromkeys(matched_urls))

    except Exception as e:
        logger.warning("stage4_extraction_failed", url=url, error=str(e))
        return []


# ============================================================================
# 목록 페이지에서 포스트 링크 추출
# ============================================================================


async def _extract_post_links(
    listing_url: str,
    config: WebScraperConfig,
) -> list[str]:
    """목록 페이지에서 포스트 링크 추출.

    Args:
        listing_url: 목록 페이지 URL
        config: 스크래핑 설정 (post_link_pattern 필수)

    Returns:
        매칭된 포스트 URL 목록 (중복 제거됨)
    """
    if not config.post_link_pattern:
        return []

    pattern = re.compile(config.post_link_pattern)
    matched_urls: list[str] = []

    try:
        if config.use_playwright_for_listing:
            # Playwright로 JavaScript 렌더링 후 링크 추출
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=BROWSER_ARGS,
                )
                page = await browser.new_page()
                await page.goto(
                    listing_url,
                    wait_until="domcontentloaded",
                    timeout=config.timeout_seconds * 1000,
                )
                # 추가 렌더링 대기
                await page.wait_for_timeout(2000)

                # 모든 링크 추출
                links = await page.evaluate(
                    """() => {
                    return Array.from(document.querySelectorAll('a[href]'))
                        .map(a => a.getAttribute('href'));
                }"""
                )
                await browser.close()

                for href in links:
                    if href and pattern.search(href):
                        full_url = urljoin(listing_url, href)
                        matched_urls.append(full_url)
        else:
            # Static HTML에서 링크 추출
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    listing_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; AXContentBot/1.0)"
                    },
                    follow_redirects=True,
                )
                response.raise_for_status()
                html = response.text

            soup = BeautifulSoup(html, "lxml")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if pattern.search(href):
                    full_url = urljoin(listing_url, href)
                    matched_urls.append(full_url)

        # 중복 제거 (순서 유지)
        unique_urls = list(dict.fromkeys(matched_urls))

        logger.info(
            "post_links_extracted",
            listing_url=listing_url,
            count=len(unique_urls),
        )

        return unique_urls[: config.max_posts]

    except Exception as e:
        logger.warning(
            "post_link_extraction_failed",
            listing_url=listing_url,
            error=str(e),
        )
        return []


async def _fetch_listing_page(
    source_id: str,
    listing_url: str,
    content_repo: ContentRepository,
    config: WebScraperConfig,
) -> list[Content]:
    """목록 페이지에서 개별 포스트들을 수집.

    Args:
        source_id: 소스 ID
        listing_url: 목록 페이지 URL
        content_repo: 콘텐츠 저장소
        config: 스크래핑 설정

    Returns:
        수집된 Content 목록
    """
    logger.info(
        "listing_mode_started",
        source_id=source_id,
        listing_url=listing_url,
        pattern=config.post_link_pattern,
    )

    # 1. 목록 페이지에서 포스트 링크 추출
    post_urls = await _extract_post_links(listing_url, config)

    if not post_urls:
        logger.warning(
            "no_post_links_found",
            listing_url=listing_url,
            pattern=config.post_link_pattern,
        )
        return []

    # 2. 각 포스트 URL에서 콘텐츠 수집
    collected_contents: list[Content] = []

    for post_url in post_urls:
        try:
            # Stage 1 시도
            scraped = await _extract_stage1_static(post_url, config)

            # Stage 1 실패 시 Stage 3 시도
            if scraped is None:
                scraped = await _extract_stage3_structural(post_url)

            # 유효한 콘텐츠면 저장
            if scraped and scraped.is_valid():
                content = await _save_scraped_content(
                    source_id=source_id,
                    scraped=scraped,
                    content_repo=content_repo,
                )
                if content:
                    collected_contents.append(content)
                    logger.debug(
                        "post_collected",
                        post_url=post_url,
                        title=scraped.title[:50],
                    )
            else:
                logger.debug(
                    "post_skipped_invalid",
                    post_url=post_url,
                    has_scraped=scraped is not None,
                )

        except Exception as e:
            logger.warning(
                "post_collection_failed",
                post_url=post_url,
                error=str(e),
            )
            continue

    logger.info(
        "listing_mode_completed",
        source_id=source_id,
        listing_url=listing_url,
        total_links=len(post_urls),
        collected=len(collected_contents),
    )

    return collected_contents


# ============================================================================
# T024: fetch_web() 함수 - 4단계 폴백 오케스트레이션
# ============================================================================


async def fetch_web(
    source_id: str,
    source_url: str,
    content_repo: ContentRepository,
    config: WebScraperConfig | None = None,
) -> list[Content]:
    """웹 페이지에서 콘텐츠 수집 (4단계 폴백).

    Args:
        source_id: 소스 ID
        source_url: 수집할 URL
        content_repo: 콘텐츠 저장소 인스턴스
        config: 스크래핑 설정 (optional)

    Returns:
        수집된 Content 목록

    Raises:
        ScrapingError: 모든 폴백 전략 실패 시
        NetworkError: 네트워크 오류 시
    """
    if config is None:
        config = WebScraperConfig()

    collected_contents: list[Content] = []

    logger.info("fetch_web_started", source_id=source_id, url=source_url)

    try:
        # 목록 모드: post_link_pattern이 설정된 경우
        if config.post_link_pattern:
            return await _fetch_listing_page(
                source_id=source_id,
                listing_url=source_url,
                content_repo=content_repo,
                config=config,
            )

        # Stage 1: Static HTML
        scraped = await _extract_stage1_static(source_url, config)

        # Stage 2: Dynamic JS (Stage 1 실패 시)
        if scraped is None:
            logger.debug("fallback_to_stage2", url=source_url)
            scraped = await _extract_stage2_dynamic(source_url, config)

        # Stage 3: Structural (Stage 2 실패 시)
        if scraped is None:
            logger.debug("fallback_to_stage3", url=source_url)
            scraped = await _extract_stage3_structural(source_url)

        # Stage 4: URL Pattern (Stage 3 실패 시)
        if scraped is None and config.url_pattern:
            logger.debug("fallback_to_stage4", url=source_url)
            matched_urls = await _extract_stage4_url_pattern(source_url, config)

            # 매칭된 각 URL에서 콘텐츠 추출 시도
            for matched_url in matched_urls[:10]:  # 최대 10개 제한
                url_scraped = await _extract_stage1_static(matched_url, config)
                if url_scraped is None:
                    url_scraped = await _extract_stage3_structural(matched_url)

                if url_scraped and url_scraped.is_valid():
                    content = await _save_scraped_content(
                        source_id=source_id,
                        scraped=url_scraped,
                        content_repo=content_repo,
                    )
                    if content:
                        collected_contents.append(content)

            if collected_contents:
                return collected_contents

        # 단일 페이지 결과 처리
        if scraped and scraped.is_valid():
            content = await _save_scraped_content(
                source_id=source_id,
                scraped=scraped,
                content_repo=content_repo,
            )
            if content:
                collected_contents.append(content)

        if not collected_contents and scraped is None:
            raise ScrapingError(
                "All extraction stages failed",
                url=source_url,
            )

        logger.info(
            "fetch_web_completed",
            source_id=source_id,
            url=source_url,
            collected_count=len(collected_contents),
        )

        return collected_contents

    except httpx.ConnectError as e:
        raise NetworkError(str(e), url=source_url) from e
    except ScrapingError:
        raise
    except Exception as e:
        logger.error(
            "fetch_web_failed", source_id=source_id, url=source_url, error=str(e)
        )
        raise ScrapingError(str(e), url=source_url) from e


# ============================================================================
# Helper functions
# ============================================================================


async def _save_scraped_content(
    source_id: str,
    scraped: ScrapedContent,
    content_repo: ContentRepository,
) -> Content | None:
    """스크래핑된 콘텐츠를 저장.

    Args:
        source_id: 소스 ID
        scraped: 스크래핑된 콘텐츠
        content_repo: 콘텐츠 저장소

    Returns:
        생성된 Content 또는 None (중복 시)
    """
    # content_key 생성 (멱등성)
    normalized_url = _normalize_url(scraped.url)
    url_hash = hashlib.sha256(normalized_url.encode()).hexdigest()[:16]
    content_key = f"{source_id}:{url_hash}"

    # 중복 체크
    if content_repo.exists_by_content_key(content_key):
        logger.debug("duplicate_content_skipped", content_key=content_key)
        return None

    # Content 생성
    now = datetime.now(UTC)
    content = Content(
        id=f"cnt_{hashlib.sha256(content_key.encode()).hexdigest()[:12]}",
        source_id=source_id,
        content_key=content_key,
        original_url=scraped.url,
        original_title=scraped.title,
        original_body=scraped.body,
        original_published_at=scraped.published_at,
        processing_status=ProcessingStatus.PENDING,
        collected_at=now,
    )

    content_repo.create(content)

    logger.info(
        "content_created",
        content_id=content.id,
        extraction_stage=scraped.extraction_stage,
    )

    return content


def _normalize_url(url: str) -> str:
    """URL 정규화."""
    parsed = urlparse(url)
    # scheme, host 소문자화, 뒤 / 제거
    normalized = (
        f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
    )
    if parsed.query:
        # 추적 파라미터 제거 (utm_*, ref, source 등)
        params = []
        for param in parsed.query.split("&"):
            key = param.split("=")[0].lower()
            if not key.startswith(("utm_", "ref", "source", "fbclid", "gclid")):
                params.append(param)
        if params:
            normalized += "?" + "&".join(params)
    return normalized


def _extract_title(element: BeautifulSoup) -> str | None:
    """요소에서 제목 추출.

    우선순위:
    1. og:title 메타 태그 (가장 정확함)
    2. <title> 태그
    3. h1 > h2 > h3 heading 태그
    """
    # 1. og:title 메타 태그 (SEO용으로 가장 정확한 제목)
    og_title = element.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title.get("content").strip()

    # 2. <title> 태그
    title_tag = element.find("title")
    if title_tag and title_tag.string:
        title = title_tag.string.strip()
        # 사이트명 분리자 처리 (예: "제목 | 사이트명" → "제목")
        for sep in [" | ", " - ", " \u2013 ", " \u2014 "]:  # EN DASH, EM DASH
            if sep in title:
                title = title.split(sep)[0].strip()
                break
        return title

    # 3. h1 > h2 > h3 순서로 검색
    for tag in ["h1", "h2", "h3"]:
        heading = element.find(tag)
        if heading:
            text = heading.get_text(strip=True)
            # "Related stories" 같은 일반적인 섹션 제목 제외
            if text.lower() not in [
                "related stories",
                "related posts",
                "more articles",
            ]:
                return text

    return None


def _extract_body_text(soup: BeautifulSoup) -> str:
    """본문 텍스트 추출 (노이즈 제거)."""
    # 노이즈 요소 제거
    for noise in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
        noise.decompose()

    # body 텍스트 추출
    body = soup.find("body")
    if body:
        return body.get_text(separator=" ", strip=True)
    return soup.get_text(separator=" ", strip=True)


def _extract_published_date(soup: BeautifulSoup) -> datetime | None:
    """발행일 추출."""
    # time 태그의 datetime 속성
    time_tag = soup.find("time", datetime=True)
    if time_tag:
        try:
            return datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    # meta 태그에서 추출
    for meta_name in ["article:published_time", "datePublished", "date"]:
        meta = soup.find("meta", {"property": meta_name}) or soup.find(
            "meta", {"name": meta_name}
        )
        if meta and meta.get("content"):
            try:
                return datetime.fromisoformat(meta["content"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

    return None
