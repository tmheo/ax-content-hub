"""Integration tests for web scraping collection flow.

Firestore 에뮬레이터와 함께 웹 스크래핑 수집 파이프라인을 테스트합니다.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.adapters.firestore_client import FirestoreClient
from src.agent.domains.collector.tools.web_scraper_tool import (
    ScrapedContent,
    fetch_web,
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


class TestWebScrapingFlowIntegration:
    """웹 스크래핑 수집 플로우 통합 테스트."""

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
    def test_web_source(
        self, source_repo: SourceRepository, test_source_id: str
    ) -> Source:
        """테스트용 WEB 소스 생성."""
        now = datetime.now(UTC)
        source_url = "https://blog.example.com/ai-article"

        # Firestore에 직접 저장
        source_repo._db.set(
            source_repo.collection_name,
            test_source_id,
            {
                "id": test_source_id,
                "name": "AI Blog",
                "type": "web",
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
            name="AI Blog",
            type=SourceType.WEB,
            url=source_url,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    @pytest.fixture
    def sample_scraped_content(self) -> ScrapedContent:
        """샘플 스크래핑 결과."""
        return ScrapedContent(
            url="https://blog.example.com/ai-article",
            title="The Future of AI in 2025",
            body="Artificial Intelligence is transforming every industry. "
            "From healthcare to finance, AI-powered solutions are becoming "
            "increasingly sophisticated. Machine learning models are now capable "
            "of understanding natural language with remarkable accuracy.",
            published_at=datetime(2024, 12, 26, 10, 0, 0, tzinfo=UTC),
        )

    @pytest.mark.asyncio
    async def test_web_scraping_creates_content_in_firestore(
        self,
        test_web_source: Source,
        content_repo: ContentRepository,
        sample_scraped_content: ScrapedContent,
    ) -> None:
        """웹 스크래핑 결과가 Firestore에 저장되는지 확인."""
        # Mock the scraper (Stage 1)
        with patch(
            "src.agent.domains.collector.tools.web_scraper_tool._extract_stage1_static",
            new_callable=AsyncMock,
            return_value=sample_scraped_content,
        ):
            # 스크래핑 실행 (fetch_web은 list[Content] 반환)
            results = await fetch_web(
                source_id=test_web_source.id,
                source_url=str(test_web_source.url),
                content_repo=content_repo,
            )

            # 콘텐츠가 생성되었는지 확인
            assert len(results) == 1
            result = results[0]
            assert result.source_id == test_web_source.id
            assert result.original_title == sample_scraped_content.title
            assert result.original_body == sample_scraped_content.body
            assert result.processing_status == ProcessingStatus.PENDING

            # Firestore에서 조회
            saved = content_repo.get_by_id(result.id)
            assert saved is not None
            assert saved.original_url == sample_scraped_content.url

    @pytest.mark.asyncio
    async def test_web_scraping_deduplication(
        self,
        test_web_source: Source,
        content_repo: ContentRepository,
        sample_scraped_content: ScrapedContent,
    ) -> None:
        """중복 URL은 다시 수집되지 않는지 확인."""
        with patch(
            "src.agent.domains.collector.tools.web_scraper_tool._extract_stage1_static",
            new_callable=AsyncMock,
            return_value=sample_scraped_content,
        ):
            # 첫 번째 수집
            first_results = await fetch_web(
                source_id=test_web_source.id,
                source_url=str(test_web_source.url),
                content_repo=content_repo,
            )
            assert len(first_results) == 1

            # 두 번째 수집 (동일 URL)
            second_results = await fetch_web(
                source_id=test_web_source.id,
                source_url=str(test_web_source.url),
                content_repo=content_repo,
            )

            # 중복이므로 빈 리스트 반환
            assert len(second_results) == 0

            # Firestore에는 하나만 존재
            all_contents = content_repo.find_by_source(test_web_source.id)
            assert len(all_contents) == 1

    @pytest.mark.asyncio
    async def test_web_scraping_stores_correct_language(
        self,
        test_web_source: Source,
        content_repo: ContentRepository,
    ) -> None:
        """스크래핑된 콘텐츠의 언어가 올바르게 저장되는지 확인."""
        unique_url = f"https://blog.example.com/korean-article-{uuid.uuid4().hex[:8]}"
        # 본문이 최소 200자 이상이어야 is_valid() 통과
        korean_content = ScrapedContent(
            url=unique_url,
            title="2025년 AI의 미래",
            body="인공지능이 모든 산업을 변화시키고 있습니다. "
            "의료에서 금융까지, AI 기반 솔루션은 점점 더 정교해지고 있습니다. "
            "머신러닝 모델은 이제 놀라운 정확도로 자연어를 이해할 수 있습니다. "
            "딥러닝 기술의 발전으로 인해 이미지 인식, 음성 인식, 자연어 처리 등 "
            "다양한 분야에서 혁신적인 성과를 거두고 있습니다. "
            "앞으로도 AI 기술은 우리 삶의 모든 영역에서 중요한 역할을 할 것입니다.",
            published_at=datetime(2024, 12, 26, 10, 0, 0, tzinfo=UTC),
        )

        with patch(
            "src.agent.domains.collector.tools.web_scraper_tool._extract_stage1_static",
            new_callable=AsyncMock,
            return_value=korean_content,
        ):
            results = await fetch_web(
                source_id=test_web_source.id,
                source_url=unique_url,
                content_repo=content_repo,
            )

            assert len(results) == 1
            # 언어 감지는 추후 구현, 현재는 기본값 확인
            assert results[0].original_language is not None

    @pytest.mark.asyncio
    async def test_web_scraping_rejects_invalid_content(
        self,
        test_web_source: Source,
        content_repo: ContentRepository,
    ) -> None:
        """본문이 최소 길이 미만인 경우 콘텐츠가 저장되지 않음을 확인."""
        unique_url = f"https://blog.example.com/short-article-{uuid.uuid4().hex[:8]}"
        # 본문이 200자 미만이므로 is_valid() 실패
        short_content = ScrapedContent(
            url=unique_url,
            title="Short Article",
            body="This is a short body that is less than 200 characters.",
            published_at=None,
        )

        with patch(
            "src.agent.domains.collector.tools.web_scraper_tool._extract_stage1_static",
            new_callable=AsyncMock,
            return_value=short_content,
        ):
            results = await fetch_web(
                source_id=test_web_source.id,
                source_url=unique_url,
                content_repo=content_repo,
            )

            # 본문이 최소 길이 미만이면 콘텐츠가 저장되지 않음
            assert len(results) == 0
