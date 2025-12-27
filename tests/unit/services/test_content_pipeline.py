"""Tests for ContentPipeline."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.models.content import Content, ProcessingStatus
from src.models.source import Source, SourceType
from src.services.content_pipeline import ContentPipeline


class TestContentPipeline:
    """Tests for ContentPipeline."""

    @pytest.fixture
    def mock_source_repo(self) -> MagicMock:
        """Mock SourceRepository."""
        return MagicMock()

    @pytest.fixture
    def mock_content_repo(self) -> MagicMock:
        """Mock ContentRepository."""
        return MagicMock()

    @pytest.fixture
    def mock_gemini_client(self) -> MagicMock:
        """Mock GeminiClient."""
        return MagicMock()

    @pytest.fixture
    def mock_tasks_client(self) -> MagicMock:
        """Mock TasksClient."""
        mock = MagicMock()
        mock.enqueue.return_value = None
        return mock

    @pytest.fixture
    def content_pipeline(
        self,
        mock_source_repo: MagicMock,
        mock_content_repo: MagicMock,
        mock_gemini_client: MagicMock,
    ) -> ContentPipeline:
        """ContentPipeline 인스턴스 (TasksClient 없음)."""
        return ContentPipeline(
            source_repo=mock_source_repo,
            content_repo=mock_content_repo,
            gemini_client=mock_gemini_client,
        )

    @pytest.fixture
    def content_pipeline_with_tasks(
        self,
        mock_source_repo: MagicMock,
        mock_content_repo: MagicMock,
        mock_gemini_client: MagicMock,
        mock_tasks_client: MagicMock,
    ) -> ContentPipeline:
        """ContentPipeline 인스턴스 (TasksClient 포함)."""
        return ContentPipeline(
            source_repo=mock_source_repo,
            content_repo=mock_content_repo,
            gemini_client=mock_gemini_client,
            tasks_client=mock_tasks_client,
        )

    @pytest.fixture
    def sample_rss_source(self) -> Source:
        """샘플 RSS 소스."""
        now = datetime.now(UTC)
        return Source(
            id="src_001",
            name="TechCrunch",
            type=SourceType.RSS,
            url="https://techcrunch.com/feed/",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    @pytest.fixture
    def sample_youtube_source(self) -> Source:
        """샘플 YouTube 소스."""
        now = datetime.now(UTC)
        return Source(
            id="src_002",
            name="AI Explained",
            type=SourceType.YOUTUBE,
            url="https://youtube.com/channel/UC123",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    @pytest.fixture
    def sample_content(self) -> Content:
        """샘플 콘텐츠."""
        now = datetime.now(UTC)
        return Content(
            id="cnt_001",
            source_id="src_001",
            content_key="src_001:abc123",
            original_url="https://example.com/article",
            original_title="GPT-5 Released",
            original_body="OpenAI announced GPT-5.",
            original_language="en",
            processing_status=ProcessingStatus.PENDING,
            collected_at=now,
        )

    def test_collect_from_sources(
        self,
        content_pipeline: ContentPipeline,
        mock_source_repo: MagicMock,
        sample_rss_source: Source,
    ) -> None:
        """활성 소스에서 콘텐츠 수집 (TasksClient 없음)."""
        mock_source_repo.find_active_sources.return_value = [sample_rss_source]

        with patch.object(
            content_pipeline, "_collect_from_rss", return_value=["cnt_001", "cnt_002"]
        ) as mock_collect:
            result = content_pipeline.collect_from_sources()

        assert result["total_sources"] == 1
        assert result["collected"] == 2
        assert result["enqueued"] == 0  # TasksClient 없으므로 0
        mock_collect.assert_called_once()

    def test_collect_from_sources_with_enqueue(
        self,
        content_pipeline_with_tasks: ContentPipeline,
        mock_source_repo: MagicMock,
        mock_tasks_client: MagicMock,
        sample_rss_source: Source,
    ) -> None:
        """활성 소스에서 콘텐츠 수집 및 처리 작업 enqueue."""
        mock_source_repo.find_active_sources.return_value = [sample_rss_source]

        with patch.object(
            content_pipeline_with_tasks,
            "_collect_from_rss",
            return_value=["cnt_001", "cnt_002", "cnt_003"],
        ):
            result = content_pipeline_with_tasks.collect_from_sources()

        assert result["total_sources"] == 1
        assert result["collected"] == 3
        assert result["enqueued"] == 3
        assert mock_tasks_client.enqueue.call_count == 3

    def test_collect_handles_multiple_source_types(
        self,
        content_pipeline: ContentPipeline,
        mock_source_repo: MagicMock,
        sample_rss_source: Source,
        sample_youtube_source: Source,
    ) -> None:
        """다양한 소스 유형 처리."""
        mock_source_repo.find_active_sources.return_value = [
            sample_rss_source,
            sample_youtube_source,
        ]

        with (
            patch.object(
                content_pipeline,
                "_collect_from_rss",
                return_value=["cnt_001", "cnt_002"],
            ),
            patch.object(
                content_pipeline, "_collect_from_youtube", return_value=["cnt_003"]
            ),
        ):
            result = content_pipeline.collect_from_sources()

        assert result["total_sources"] == 2
        assert result["collected"] == 3

    def test_collect_with_error_handling(
        self,
        content_pipeline: ContentPipeline,
        mock_source_repo: MagicMock,
        sample_rss_source: Source,
    ) -> None:
        """수집 중 에러 처리."""
        mock_source_repo.find_active_sources.return_value = [sample_rss_source]

        with patch.object(
            content_pipeline,
            "_collect_from_rss",
            side_effect=Exception("RSS fetch error"),
        ):
            result = content_pipeline.collect_from_sources()

        # 에러가 발생해도 결과 반환
        assert result["total_sources"] == 1
        assert result["errors"] >= 1

    def test_process_single_content_success(
        self,
        content_pipeline: ContentPipeline,
        mock_content_repo: MagicMock,
        sample_content: Content,
    ) -> None:
        """단일 콘텐츠 처리 성공."""
        with (
            patch("src.services.content_pipeline.translate_content") as mock_translate,
            patch("src.services.content_pipeline.summarize_content") as mock_summarize,
            patch("src.services.content_pipeline.score_relevance") as mock_score,
        ):
            mock_translate.return_value = MagicMock(
                title_ko="번역된 제목",
                body_ko="번역된 본문",
            )
            mock_summarize.return_value = MagicMock(
                title_ko="요약 제목",
                summary_ko="요약 내용",
                why_important="중요한 이유",
                categories=["AI"],
            )
            mock_score.return_value = MagicMock(score=0.85)

            result = content_pipeline._process_single_content(sample_content)

        assert result is True
        mock_content_repo.update_processing_result.assert_called_once()

    def test_process_single_content_failure(
        self,
        content_pipeline: ContentPipeline,
        mock_content_repo: MagicMock,
        sample_content: Content,
    ) -> None:
        """단일 콘텐츠 처리 실패."""
        with patch(
            "src.services.content_pipeline.translate_content",
            side_effect=Exception("Translation failed"),
        ):
            result = content_pipeline._process_single_content(sample_content)

        assert result is False
        mock_content_repo.increment_processing_attempts.assert_called_once()

    def test_handle_process_task(
        self,
        content_pipeline: ContentPipeline,
        mock_content_repo: MagicMock,
        sample_content: Content,
    ) -> None:
        """Cloud Tasks process 핸들러 테스트."""
        mock_content_repo.get_by_id.return_value = sample_content

        with patch.object(
            content_pipeline, "_process_single_content", return_value=True
        ):
            # 정상 호출
            content_pipeline._handle_process_task({"content_id": "cnt_001"})

        mock_content_repo.get_by_id.assert_called_with("cnt_001")

    def test_handle_process_task_content_not_found(
        self,
        content_pipeline: ContentPipeline,
        mock_content_repo: MagicMock,
    ) -> None:
        """존재하지 않는 콘텐츠 처리 시도."""
        mock_content_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Content not found"):
            content_pipeline._handle_process_task({"content_id": "cnt_999"})

    def test_handle_process_task_missing_content_id(
        self,
        content_pipeline: ContentPipeline,
    ) -> None:
        """content_id 누락."""
        with pytest.raises(ValueError, match="content_id is required"):
            content_pipeline._handle_process_task({})

    def test_tasks_client_handler_registration(
        self,
        mock_source_repo: MagicMock,
        mock_content_repo: MagicMock,
        mock_gemini_client: MagicMock,
        mock_tasks_client: MagicMock,
    ) -> None:
        """TasksClient에 핸들러 등록 확인."""
        ContentPipeline(
            source_repo=mock_source_repo,
            content_repo=mock_content_repo,
            gemini_client=mock_gemini_client,
            tasks_client=mock_tasks_client,
        )

        mock_tasks_client.register_handler.assert_called_once()
        call_args = mock_tasks_client.register_handler.call_args
        assert call_args[0][0] == "process"


class TestContentPipelineIntegration:
    """Integration-style tests for ContentPipeline."""

    def test_empty_sources_returns_zero(self) -> None:
        """소스가 없으면 0 반환."""
        mock_source_repo = MagicMock()
        mock_content_repo = MagicMock()
        mock_gemini = MagicMock()

        mock_source_repo.find_active_sources.return_value = []

        pipeline = ContentPipeline(
            source_repo=mock_source_repo,
            content_repo=mock_content_repo,
            gemini_client=mock_gemini,
        )

        result = pipeline.collect_from_sources()

        assert result["total_sources"] == 0
        assert result["collected"] == 0
        assert result["enqueued"] == 0
