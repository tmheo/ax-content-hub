"""Integration tests for RSS collection flow.

Firestore 에뮬레이터와 함께 RSS 수집 파이프라인을 테스트합니다.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.firestore_client import FirestoreClient
from src.agent.domains.collector.tools.rss_tool import RSSEntry
from src.models.source import Source, SourceType
from src.repositories.content_repo import ContentRepository
from src.repositories.source_repo import SourceRepository
from src.services.content_pipeline import ContentPipeline
from tests.utils import is_emulator_available

# Firestore 에뮬레이터가 없으면 테스트 스킵
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not is_emulator_available(),
        reason="Firestore emulator not available at FIRESTORE_EMULATOR_HOST",
    ),
]


class TestCollectionFlowIntegration:
    """RSS 수집 플로우 통합 테스트."""

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
    def test_source(self, source_repo: SourceRepository, test_source_id: str) -> Source:
        """테스트용 RSS 소스 생성."""
        now = datetime.now(UTC)
        source_url = "https://test.example.com/feed.xml"

        # Firestore에 직접 저장 (HttpUrl 직렬화 문제 회피)
        source_repo._db.set(
            source_repo.collection_name,
            test_source_id,
            {
                "id": test_source_id,
                "name": "Test Tech Blog",
                "type": "rss",
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
            name="Test Tech Blog",
            type=SourceType.RSS,
            url=source_url,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    @pytest.fixture
    def sample_rss_entries(self) -> list[RSSEntry]:
        """샘플 RSS 엔트리."""
        return [
            RSSEntry(
                title="GPT-5 Announced: A New Era of AI",
                url="https://test.example.com/gpt-5-announced",
                body="OpenAI has announced GPT-5.",
                published_at=datetime(2024, 12, 26, 9, 0, 0, tzinfo=UTC),
            ),
            RSSEntry(
                title="Machine Learning in 2025: Trends to Watch",
                url="https://test.example.com/ml-trends-2025",
                body="Top ML trends expected in 2025.",
                published_at=datetime(2024, 12, 25, 10, 0, 0, tzinfo=UTC),
            ),
            RSSEntry(
                title="Breaking: New AI Regulation Proposed",
                url="https://test.example.com/ai-regulation",
                body="Governments propose new AI regulation.",
                published_at=datetime(2024, 12, 24, 8, 0, 0, tzinfo=UTC),
            ),
        ]

    def test_collect_rss_creates_contents_in_firestore(
        self,
        source_repo: SourceRepository,
        content_repo: ContentRepository,
        test_source: Source,
        sample_rss_entries: list[RSSEntry],
    ) -> None:
        """RSS 수집 시 Firestore에 콘텐츠가 생성되는지 확인."""
        # Mock parse_rss_feed to return sample entries
        with patch(
            "src.agent.domains.collector.tools.rss_tool.parse_rss_feed",
            return_value=sample_rss_entries,
        ):
            pipeline = ContentPipeline(
                source_repo=source_repo,
                content_repo=content_repo,
                gemini_client=MagicMock(),
            )

            result = pipeline.collect_from_sources()

            # 검증
            assert result["total_sources"] == 1
            assert result["collected"] == 3  # 3개 아이템
            assert result["errors"] == 0

            # Firestore에서 콘텐츠 확인
            contents = content_repo.find_by_source(test_source.id)
            assert len(contents) == 3

            # 콘텐츠 내용 확인
            titles = {c.original_title for c in contents}
            assert "GPT-5 Announced: A New Era of AI" in titles
            assert "Machine Learning in 2025: Trends to Watch" in titles
            assert "Breaking: New AI Regulation Proposed" in titles

    def test_collect_rss_skips_duplicates(
        self,
        source_repo: SourceRepository,
        content_repo: ContentRepository,
        test_source: Source,
        sample_rss_entries: list[RSSEntry],
    ) -> None:
        """중복 콘텐츠는 수집하지 않음."""
        with patch(
            "src.agent.domains.collector.tools.rss_tool.parse_rss_feed",
            return_value=sample_rss_entries,
        ):
            pipeline = ContentPipeline(
                source_repo=source_repo,
                content_repo=content_repo,
                gemini_client=MagicMock(),
            )

            # 첫 번째 수집
            result1 = pipeline.collect_from_sources()
            assert result1["collected"] == 3

            # 두 번째 수집 (중복)
            result2 = pipeline.collect_from_sources()

            # 중복이므로 0개 수집
            assert result2["collected"] == 0

            # Firestore에는 여전히 3개만 존재
            contents = content_repo.find_by_source(test_source.id)
            assert len(contents) == 3

    def test_collect_with_tasks_client_enqueues_processing(
        self,
        source_repo: SourceRepository,
        content_repo: ContentRepository,
        test_source: Source,
        sample_rss_entries: list[RSSEntry],
    ) -> None:
        """TasksClient가 있으면 처리 작업이 enqueue됨."""
        with patch(
            "src.agent.domains.collector.tools.rss_tool.parse_rss_feed",
            return_value=sample_rss_entries,
        ):
            mock_tasks = MagicMock()
            mock_tasks.enqueue.return_value = None

            pipeline = ContentPipeline(
                source_repo=source_repo,
                content_repo=content_repo,
                gemini_client=MagicMock(),
                tasks_client=mock_tasks,
            )

            result = pipeline.collect_from_sources()

            assert result["collected"] == 3
            assert result["enqueued"] == 3
            assert mock_tasks.enqueue.call_count == 3

            # enqueue 호출 확인
            for call in mock_tasks.enqueue.call_args_list:
                task_type, payload = call[0]
                assert task_type == "process"
                assert "content_id" in payload

    def test_collect_handles_rss_fetch_error(
        self,
        source_repo: SourceRepository,
        content_repo: ContentRepository,
        test_source: Source,
    ) -> None:
        """RSS 피드 에러 시 에러 카운트 증가."""
        # 에러 발생 모킹
        with patch(
            "src.agent.domains.collector.tools.rss_tool.parse_rss_feed",
            side_effect=ValueError("Failed to parse RSS feed"),
        ):
            pipeline = ContentPipeline(
                source_repo=source_repo,
                content_repo=content_repo,
                gemini_client=MagicMock(),
            )

            result = pipeline.collect_from_sources()

            assert result["errors"] >= 1
            assert result["collected"] == 0

            # 소스의 에러 카운트 확인
            updated_source = source_repo.get_by_id(test_source.id)
            assert updated_source is not None
            assert updated_source.fetch_error_count >= 1

    def test_collect_inactive_source_not_processed(
        self,
        source_repo: SourceRepository,
        content_repo: ContentRepository,
        firestore_client: FirestoreClient,
    ) -> None:
        """비활성 소스는 수집하지 않음."""
        # 비활성 소스 생성 (Firestore에 직접 저장)
        now = datetime.now(UTC)
        source_id = f"src_inactive_{uuid.uuid4().hex[:8]}"
        source_url = "https://inactive.example.com/feed.xml"

        source_repo._db.set(
            source_repo.collection_name,
            source_id,
            {
                "id": source_id,
                "name": "Inactive Blog",
                "type": "rss",
                "url": source_url,
                "is_active": False,
                "created_at": now,
                "updated_at": now,
                "config": {},
                "language": "en",
                "fetch_error_count": 0,
            },
        )

        pipeline = ContentPipeline(
            source_repo=source_repo,
            content_repo=content_repo,
            gemini_client=MagicMock(),
        )

        result = pipeline.collect_from_sources()

        # 비활성 소스는 find_active_sources에서 제외됨
        assert result["total_sources"] == 0
        assert result["collected"] == 0

    def test_collect_updates_source_last_fetched(
        self,
        source_repo: SourceRepository,
        content_repo: ContentRepository,
        test_source: Source,
        sample_rss_entries: list[RSSEntry],
    ) -> None:
        """수집 성공 시 소스의 last_fetched_at 업데이트."""
        with patch(
            "src.agent.domains.collector.tools.rss_tool.parse_rss_feed",
            return_value=sample_rss_entries,
        ):
            # 초기 last_fetched_at 확인
            initial_source = source_repo.get_by_id(test_source.id)
            assert initial_source is not None
            initial_last_fetched = initial_source.last_fetched_at

            pipeline = ContentPipeline(
                source_repo=source_repo,
                content_repo=content_repo,
                gemini_client=MagicMock(),
            )

            pipeline.collect_from_sources()

            # Firestore에서 콘텐츠 확인
            contents = content_repo.find_by_source(test_source.id)
            assert len(contents) == 3

            # last_fetched_at 업데이트 확인
            updated_source = source_repo.get_by_id(test_source.id)
            assert updated_source is not None
            assert updated_source.last_fetched_at is not None
            if initial_last_fetched is not None:
                assert updated_source.last_fetched_at > initial_last_fetched

    def test_collect_preserves_content_metadata(
        self,
        source_repo: SourceRepository,
        content_repo: ContentRepository,
        test_source: Source,
        sample_rss_entries: list[RSSEntry],
    ) -> None:
        """수집된 콘텐츠의 메타데이터가 보존됨."""
        with patch(
            "src.agent.domains.collector.tools.rss_tool.parse_rss_feed",
            return_value=sample_rss_entries,
        ):
            pipeline = ContentPipeline(
                source_repo=source_repo,
                content_repo=content_repo,
                gemini_client=MagicMock(),
            )

            pipeline.collect_from_sources()

            # Firestore에서 콘텐츠 확인
            contents = content_repo.find_by_source(test_source.id)

            for content in contents:
                assert content.source_id == test_source.id
                assert content.original_url is not None
                assert content.original_title is not None
                assert content.collected_at is not None
                assert content.content_key.startswith(test_source.id)
