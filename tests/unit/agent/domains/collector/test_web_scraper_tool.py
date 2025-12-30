"""Tests for web_scraper_tool.

웹 스크래핑 도구의 4단계 폴백 전략을 테스트합니다.
TDD: Red → Green → Refactor
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.repositories.content_repo import ContentRepository

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_content_repo() -> MagicMock:
    """Mock ContentRepository fixture."""
    repo = MagicMock(spec=ContentRepository)
    repo.exists_by_content_key.return_value = False
    repo.create.return_value = MagicMock(id="content_001")
    return repo


@pytest.fixture
def sample_html_static() -> str:
    """정적 HTML 샘플 (Stage 1 테스트용)."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Blog Post</title></head>
    <body>
        <article class="blog-post">
            <h1>AI Revolution in 2025</h1>
            <time datetime="2025-01-15">January 15, 2025</time>
            <div class="content">
                This is a comprehensive article about AI developments.
                It covers various topics including machine learning,
                natural language processing, and computer vision.
                The article provides insights into future trends.
            </div>
        </article>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_dynamic() -> str:
    """동적 HTML 샘플 (Stage 2 테스트용)."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Dynamic Blog</title></head>
    <body>
        <div id="app">
            <div class="post-container">
                <h2 class="title">Understanding LLMs</h2>
                <p class="body">Large Language Models are transforming how we interact with AI.
                This post explains the fundamentals of transformer architecture
                and how modern LLMs achieve their remarkable capabilities.</p>
            </div>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_structural() -> str:
    """구조적 HTML 샘플 (Stage 3 테스트용)."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Tech News</title></head>
    <body>
        <header>Site Header</header>
        <nav>Navigation</nav>
        <main>
            <h1>Breaking: New AI Breakthrough</h1>
            <p>Scientists have announced a major breakthrough in artificial intelligence.
            The new model can perform complex reasoning tasks with unprecedented accuracy.
            This development has significant implications for various industries.</p>
        </main>
        <footer>Site Footer</footer>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_with_links() -> str:
    """링크가 있는 HTML 샘플 (Stage 4 테스트용)."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Blog Index</title></head>
    <body>
        <div class="blog-list">
            <a href="/blog/2025/01/post-1">First Post Title</a>
            <a href="/blog/2025/01/post-2">Second Post Title</a>
            <a href="/about">About Us</a>
            <a href="/blog/2024/12/old-post">Old Post</a>
        </div>
    </body>
    </html>
    """


# ============================================================================
# T011: WebScraperConfig, ScrapedContent dataclass 테스트
# ============================================================================


class TestWebScraperConfig:
    """WebScraperConfig dataclass 테스트."""

    def test_default_values(self) -> None:
        """기본값으로 생성."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
        )

        config = WebScraperConfig()
        assert config.selector is None
        assert config.wait_for is None
        assert config.url_pattern is None
        assert config.timeout_seconds == 30

    def test_custom_values(self) -> None:
        """커스텀 값으로 생성."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
        )

        config = WebScraperConfig(
            selector=".blog-post",
            wait_for=".content-loaded",
            url_pattern=r"/blog/\d{4}/",
            timeout_seconds=60,
        )
        assert config.selector == ".blog-post"
        assert config.wait_for == ".content-loaded"
        assert config.url_pattern == r"/blog/\d{4}/"
        assert config.timeout_seconds == 60

    def test_from_source_config(self) -> None:
        """Source.config에서 생성."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
        )

        source_config = {
            "selector": ".article",
            "wait_for": ".loaded",
            "url_pattern": "/post/",
            "timeout_seconds": 45,
        }
        config = WebScraperConfig.from_source_config(source_config)
        assert config.selector == ".article"
        assert config.wait_for == ".loaded"
        assert config.url_pattern == "/post/"
        assert config.timeout_seconds == 45

    def test_from_source_config_with_defaults(self) -> None:
        """Source.config에서 생성 (기본값 사용)."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
        )

        config = WebScraperConfig.from_source_config({})
        assert config.selector is None
        assert config.timeout_seconds == 30

    def test_immutable(self) -> None:
        """frozen=True 확인."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
        )

        config = WebScraperConfig()
        with pytest.raises(AttributeError):
            config.selector = ".new-selector"  # type: ignore[misc]


class TestScrapedContent:
    """ScrapedContent dataclass 테스트."""

    def test_creation(self) -> None:
        """기본 생성."""
        from src.agent.domains.collector.tools.web_scraper_tool import ScrapedContent

        content = ScrapedContent(
            url="https://example.com/post/1",
            title="Test Title",
            body="This is the body content with enough length for validation.",
            published_at=datetime(2025, 1, 15),
            extraction_stage=1,
        )
        assert content.url == "https://example.com/post/1"
        assert content.title == "Test Title"
        assert content.extraction_stage == 1

    def test_default_values(self) -> None:
        """기본값 확인."""
        from src.agent.domains.collector.tools.web_scraper_tool import ScrapedContent

        content = ScrapedContent(
            url="https://example.com/post",
            title="Title",
            body="Body content",
        )
        assert content.published_at is None
        assert content.extraction_stage == 0

    def test_is_valid_success(self) -> None:
        """유효한 콘텐츠."""
        from src.agent.domains.collector.tools.web_scraper_tool import ScrapedContent

        content = ScrapedContent(
            url="https://example.com/post",
            title="Valid Title",
            body="A" * 200,  # 200자 이상
        )
        assert content.is_valid(min_body_length=200) is True

    def test_is_valid_short_body(self) -> None:
        """본문 길이 미달."""
        from src.agent.domains.collector.tools.web_scraper_tool import ScrapedContent

        content = ScrapedContent(
            url="https://example.com/post",
            title="Valid Title",
            body="Short",
        )
        assert content.is_valid(min_body_length=200) is False

    def test_is_valid_no_title(self) -> None:
        """제목 없음."""
        from src.agent.domains.collector.tools.web_scraper_tool import ScrapedContent

        content = ScrapedContent(
            url="https://example.com/post",
            title="",
            body="A" * 200,
        )
        assert content.is_valid() is False


# ============================================================================
# T012: Stage 1 (Static HTML) 추출 테스트
# ============================================================================


class TestStage1StaticExtraction:
    """Stage 1: Static HTML 추출 테스트."""

    @pytest.mark.asyncio
    async def test_extract_with_selector(
        self, sample_html_static: str, mock_content_repo: MagicMock
    ) -> None:
        """CSS selector로 정적 콘텐츠 추출."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
            _extract_stage1_static,
        )

        config = WebScraperConfig(selector=".blog-post")

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = sample_html_static
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await _extract_stage1_static(
                url="https://example.com/blog/post-1",
                config=config,
            )

        assert result is not None
        assert result.extraction_stage == 1
        assert "AI Revolution" in result.title or "AI" in result.body

    @pytest.mark.asyncio
    async def test_extract_without_selector(self, sample_html_static: str) -> None:
        """selector 없이 기본 추출."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
            _extract_stage1_static,
        )

        config = WebScraperConfig()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = sample_html_static
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await _extract_stage1_static(
                url="https://example.com/blog/post-1",
                config=config,
            )

        assert result is not None
        # title 태그가 추출됨 (og:title → title → h1 순서)
        assert result.title == "Test Blog Post"

    @pytest.mark.asyncio
    async def test_extract_returns_none_on_short_content(self) -> None:
        """콘텐츠 길이 미달 시 None 반환."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
            _extract_stage1_static,
        )

        short_html = "<html><body><p>Short</p></body></html>"
        config = WebScraperConfig()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = short_html
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await _extract_stage1_static(
                url="https://example.com/short",
                config=config,
            )

        assert result is None


# ============================================================================
# T013: Stage 2 (Dynamic JS) 추출 테스트
# ============================================================================


class TestStage2DynamicExtraction:
    """Stage 2: Dynamic JS 추출 테스트."""

    @pytest.mark.asyncio
    async def test_extract_with_playwright(self, sample_html_dynamic: str) -> None:
        """Playwright로 동적 콘텐츠 추출."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
            _extract_stage2_dynamic,
        )

        config = WebScraperConfig(
            selector=".post-container",
            wait_for=".post-container",
        )

        with patch(
            "src.agent.domains.collector.tools.web_scraper_tool.async_playwright"
        ) as mock_pw:
            # Mock Playwright
            mock_page = AsyncMock()
            mock_page.content.return_value = sample_html_dynamic
            mock_page.wait_for_selector = AsyncMock()

            mock_context = AsyncMock()
            mock_context.new_page.return_value = mock_page

            mock_browser = AsyncMock()
            mock_browser.new_context.return_value = mock_context

            mock_pw_instance = AsyncMock()
            mock_pw_instance.chromium.launch.return_value = mock_browser
            mock_pw.return_value.__aenter__.return_value = mock_pw_instance

            result = await _extract_stage2_dynamic(
                url="https://example.com/dynamic",
                config=config,
            )

        assert result is not None
        assert result.extraction_stage == 2

    @pytest.mark.asyncio
    async def test_extract_handles_timeout(self) -> None:
        """타임아웃 처리."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
            _extract_stage2_dynamic,
        )

        config = WebScraperConfig(timeout_seconds=1)

        with patch(
            "src.agent.domains.collector.tools.web_scraper_tool.async_playwright"
        ) as mock_pw:
            mock_pw_instance = AsyncMock()
            mock_pw_instance.chromium.launch.side_effect = TimeoutError("Timeout")
            mock_pw.return_value.__aenter__.return_value = mock_pw_instance

            result = await _extract_stage2_dynamic(
                url="https://example.com/slow",
                config=config,
            )

        assert result is None


# ============================================================================
# T014: Stage 3 (Structural) 추출 테스트
# ============================================================================


class TestStage3StructuralExtraction:
    """Stage 3: Structural 추출 테스트."""

    @pytest.mark.asyncio
    async def test_extract_main_content(self, sample_html_structural: str) -> None:
        """main 태그에서 콘텐츠 추출."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            _extract_stage3_structural,
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = sample_html_structural
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await _extract_stage3_structural(
                url="https://example.com/news",
            )

        assert result is not None
        assert result.extraction_stage == 3
        assert (
            "AI Breakthrough" in result.title or "breakthrough" in result.body.lower()
        )

    @pytest.mark.asyncio
    async def test_fallback_to_article_tag(self) -> None:
        """article 태그로 폴백."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            _extract_stage3_structural,
        )

        html = """
        <html><body>
            <article>
                <h2>Article Title</h2>
                <p>This is article content with sufficient length for extraction.
                It contains multiple sentences to pass the minimum length check.
                We need to add more text to ensure the content exceeds the minimum
                threshold of 200 characters. This additional text should make the
                article content long enough to pass all validation checks.</p>
            </article>
        </body></html>
        """

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = html
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await _extract_stage3_structural(
                url="https://example.com/article",
            )

        assert result is not None
        assert "Article Title" in result.title or "article" in result.body.lower()


# ============================================================================
# T015: Stage 4 (URL Pattern) 추출 테스트
# ============================================================================


class TestStage4URLPatternExtraction:
    """Stage 4: URL Pattern 추출 테스트."""

    @pytest.mark.asyncio
    async def test_extract_links_with_pattern(
        self, sample_html_with_links: str
    ) -> None:
        """URL 패턴으로 링크 추출."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
            _extract_stage4_url_pattern,
        )

        config = WebScraperConfig(url_pattern=r"/blog/2025/")

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = sample_html_with_links
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await _extract_stage4_url_pattern(
                url="https://example.com/blog",
                config=config,
            )

        assert result is not None
        assert len(result) == 2  # 2025년 포스트 2개만
        assert all("/blog/2025/" in url for url in result)

    @pytest.mark.asyncio
    async def test_returns_empty_without_pattern(
        self, sample_html_with_links: str
    ) -> None:
        """패턴 없으면 빈 리스트 반환."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
            _extract_stage4_url_pattern,
        )

        config = WebScraperConfig()  # url_pattern 없음

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = sample_html_with_links
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await _extract_stage4_url_pattern(
                url="https://example.com/blog",
                config=config,
            )

        assert result == []


# ============================================================================
# T016: fetch_web() 4단계 폴백 오케스트레이션 테스트
# ============================================================================


class TestFetchWebOrchestration:
    """fetch_web() 오케스트레이션 테스트."""

    @pytest.mark.asyncio
    async def test_success_at_stage1(
        self, mock_content_repo: MagicMock, sample_html_static: str
    ) -> None:
        """Stage 1에서 성공."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
            fetch_web,
        )

        config = WebScraperConfig(selector=".blog-post")

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = sample_html_static
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await fetch_web(
                source_id="src_web_001",
                source_url="https://example.com/blog",
                content_repo=mock_content_repo,
                config=config,
            )

        assert len(result) >= 1
        mock_content_repo.create.assert_called()

    @pytest.mark.asyncio
    async def test_fallback_to_stage2(
        self, mock_content_repo: MagicMock, sample_html_dynamic: str
    ) -> None:
        """Stage 1 실패 시 Stage 2로 폴백."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
            fetch_web,
        )

        config = WebScraperConfig(selector=".post-container")

        with (
            patch(
                "src.agent.domains.collector.tools.web_scraper_tool._extract_stage1_static"
            ) as mock_s1,
            patch(
                "src.agent.domains.collector.tools.web_scraper_tool._extract_stage2_dynamic"
            ) as mock_s2,
        ):
            # Stage 1 실패
            mock_s1.return_value = None

            # Stage 2 성공
            from src.agent.domains.collector.tools.web_scraper_tool import (
                ScrapedContent,
            )

            mock_s2.return_value = ScrapedContent(
                url="https://example.com/dynamic",
                title="Dynamic Title",
                body="A" * 250,
                extraction_stage=2,
            )

            result = await fetch_web(
                source_id="src_web_001",
                source_url="https://example.com/blog",
                content_repo=mock_content_repo,
                config=config,
            )

        assert len(result) == 1
        mock_s1.assert_called_once()
        mock_s2.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_duplicate_content(
        self, mock_content_repo: MagicMock, sample_html_static: str
    ) -> None:
        """중복 콘텐츠 건너뜀."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            WebScraperConfig,
            fetch_web,
        )

        mock_content_repo.exists_by_content_key.return_value = True
        config = WebScraperConfig()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = sample_html_static
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await fetch_web(
                source_id="src_web_001",
                source_url="https://example.com/blog",
                content_repo=mock_content_repo,
                config=config,
            )

        assert len(result) == 0
        mock_content_repo.create.assert_not_called()


# ============================================================================
# T017: 예외 처리 테스트
# ============================================================================


class TestExceptionHandling:
    """예외 처리 테스트."""

    def test_scraping_error(self) -> None:
        """ScrapingError 생성."""
        from src.agent.domains.collector.tools.web_scraper_tool import ScrapingError

        error = ScrapingError("Failed to scrape", url="https://example.com")
        assert "Failed to scrape" in str(error)
        assert error.url == "https://example.com"

    def test_network_error(self) -> None:
        """NetworkError 생성."""
        from src.agent.domains.collector.tools.web_scraper_tool import NetworkError

        error = NetworkError("Connection failed", url="https://example.com")
        assert "Connection failed" in str(error)

    @pytest.mark.asyncio
    async def test_fetch_web_raises_on_all_stages_fail(
        self, mock_content_repo: MagicMock
    ) -> None:
        """모든 Stage 실패 시 ScrapingError 발생."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            ScrapingError,
            WebScraperConfig,
            fetch_web,
        )

        config = WebScraperConfig()

        with (
            patch(
                "src.agent.domains.collector.tools.web_scraper_tool._extract_stage1_static"
            ) as mock_s1,
            patch(
                "src.agent.domains.collector.tools.web_scraper_tool._extract_stage2_dynamic"
            ) as mock_s2,
            patch(
                "src.agent.domains.collector.tools.web_scraper_tool._extract_stage3_structural"
            ) as mock_s3,
            patch(
                "src.agent.domains.collector.tools.web_scraper_tool._extract_stage4_url_pattern"
            ) as mock_s4,
        ):
            mock_s1.return_value = None
            mock_s2.return_value = None
            mock_s3.return_value = None
            mock_s4.return_value = []

            with pytest.raises(ScrapingError):
                await fetch_web(
                    source_id="src_web_001",
                    source_url="https://example.com/blog",
                    content_repo=mock_content_repo,
                    config=config,
                )

    @pytest.mark.asyncio
    async def test_network_error_on_connection_failure(
        self, mock_content_repo: MagicMock
    ) -> None:
        """네트워크 연결 실패 시 ScrapingError (모든 스테이지 실패)."""
        from src.agent.domains.collector.tools.web_scraper_tool import (
            ScrapingError,
            fetch_web,
        )

        with patch("httpx.AsyncClient") as mock_client:
            import httpx

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            # 모든 스테이지가 실패하면 ScrapingError 발생
            with pytest.raises(ScrapingError) as exc_info:
                await fetch_web(
                    source_id="src_web_001",
                    source_url="https://example.com/unreachable",
                    content_repo=mock_content_repo,
                )
            assert "All extraction stages failed" in str(exc_info.value)
