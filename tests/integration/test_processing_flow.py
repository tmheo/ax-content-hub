"""Integration tests for content processing flow.

Firestore 에뮬레이터와 함께 콘텐츠 처리 파이프라인을 테스트합니다.
번역 → 요약 → 스코어링 전체 플로우를 검증합니다.
"""

import os
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.firestore_client import FirestoreClient
from src.adapters.gemini_client import GeminiClient
from src.models.content import Content, ProcessingStatus
from src.repositories.content_repo import ContentRepository
from src.repositories.source_repo import SourceRepository
from src.services.content_pipeline import ContentPipeline


def is_emulator_available() -> bool:
    """Firestore 에뮬레이터 사용 가능 여부 확인."""
    import socket

    host = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8086")
    host_parts = host.split(":")
    hostname = host_parts[0]
    port = int(host_parts[1]) if len(host_parts) > 1 else 8086

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((hostname, port))
        sock.close()
        return result == 0
    except Exception:
        return False


# Firestore 에뮬레이터가 없으면 테스트 스킵
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not is_emulator_available(),
        reason="Firestore emulator not available at FIRESTORE_EMULATOR_HOST",
    ),
]


class TestProcessingFlowIntegration:
    """콘텐츠 처리 플로우 통합 테스트."""

    @pytest.fixture
    def firestore_client(self) -> FirestoreClient:
        """실제 Firestore 에뮬레이터 클라이언트."""
        return FirestoreClient(project_id="ax-content-hub-test")

    @pytest.fixture
    def source_repo(self, firestore_client: FirestoreClient) -> SourceRepository:
        """SourceRepository with real Firestore."""
        return SourceRepository(firestore_client)

    @pytest.fixture
    def content_repo(self, firestore_client: FirestoreClient) -> ContentRepository:
        """ContentRepository with real Firestore."""
        return ContentRepository(firestore_client)

    @pytest.fixture
    def mock_gemini_client(self) -> MagicMock:
        """Mock GeminiClient."""
        return MagicMock(spec=GeminiClient)

    @pytest.fixture
    def test_content(self, content_repo: ContentRepository) -> Content:
        """테스트용 콘텐츠 생성."""
        now = datetime.now(UTC)
        content = Content(
            id=f"cnt_test_{uuid.uuid4().hex[:8]}",
            source_id="src_test_001",
            content_key=f"src_test_001:{uuid.uuid4().hex[:16]}",
            original_url="https://test.example.com/article-1",
            original_title="GPT-5 Announced: A New Era of AI",
            original_body=(
                "OpenAI has announced GPT-5, the next generation of their AI model. "
                "This new model brings significant improvements in reasoning, "
                "multimodal capabilities, and efficiency. The announcement was made "
                "at the company's annual developer conference."
            ),
            original_language="en",
            processing_status=ProcessingStatus.PENDING,
            collected_at=now,
        )
        content_repo.create(content)
        return content

    @pytest.fixture
    def cleanup_content(
        self,
        content_repo: ContentRepository,
        test_content: Content,
    ) -> None:
        """테스트 후 콘텐츠 정리."""
        yield
        try:
            content_repo.delete(test_content.id)
        except Exception:
            pass

    def test_process_single_content_updates_firestore(
        self,
        source_repo: SourceRepository,
        content_repo: ContentRepository,
        mock_gemini_client: MagicMock,
        test_content: Content,
        cleanup_content: None,
    ) -> None:
        """단일 콘텐츠 처리 시 Firestore가 업데이트되는지 확인."""
        # Mock processing results
        with (
            patch("src.services.content_pipeline.translate_content") as mock_translate,
            patch("src.services.content_pipeline.summarize_content") as mock_summarize,
            patch("src.services.content_pipeline.score_relevance") as mock_score,
        ):
            mock_translate.return_value = MagicMock(
                title_ko="GPT-5 발표: AI의 새로운 시대",
                body_ko=(
                    "OpenAI가 GPT-5를 발표했습니다. 차세대 AI 모델로서 "
                    "추론 능력, 멀티모달 기능, 효율성에서 크게 향상되었습니다."
                ),
            )
            mock_summarize.return_value = MagicMock(
                title_ko="GPT-5 발표",
                summary_ko="OpenAI가 GPT-5를 발표. 추론, 멀티모달, 효율성 대폭 개선.",
                why_important="최신 AI 기술 동향을 이해하는 데 필수적인 정보",
                categories=["AI", "LLM", "OpenAI"],
            )
            mock_score.return_value = MagicMock(score=0.92)

            pipeline = ContentPipeline(
                source_repo=source_repo,
                content_repo=content_repo,
                gemini_client=mock_gemini_client,
            )

            # 처리 실행
            result = pipeline._process_single_content(test_content)

            # 성공 확인
            assert result is True

            # Firestore에서 업데이트된 콘텐츠 확인
            updated_content = content_repo.get_by_id(test_content.id)
            assert updated_content is not None
            assert updated_content.title_ko == "GPT-5 발표"
            assert updated_content.summary_ko is not None
            assert "GPT-5" in updated_content.summary_ko
            assert updated_content.why_important is not None
            assert updated_content.relevance_score == 0.92
            assert updated_content.categories == ["AI", "LLM", "OpenAI"]
            assert updated_content.processing_status == ProcessingStatus.COMPLETED

    def test_process_single_content_handles_translation_error(
        self,
        source_repo: SourceRepository,
        content_repo: ContentRepository,
        mock_gemini_client: MagicMock,
        test_content: Content,
        cleanup_content: None,
    ) -> None:
        """번역 에러 시 처리 실패 및 재시도 카운트 증가."""
        with patch(
            "src.services.content_pipeline.translate_content",
            side_effect=Exception("Gemini API rate limit exceeded"),
        ):
            pipeline = ContentPipeline(
                source_repo=source_repo,
                content_repo=content_repo,
                gemini_client=mock_gemini_client,
            )

            result = pipeline._process_single_content(test_content)

            # 실패 확인
            assert result is False

            # Firestore에서 에러 상태 확인
            updated_content = content_repo.get_by_id(test_content.id)
            assert updated_content is not None
            assert updated_content.processing_attempts >= 1
            assert updated_content.last_error is not None
            assert "rate limit" in updated_content.last_error.lower()

    def test_process_via_handle_process_task(
        self,
        source_repo: SourceRepository,
        content_repo: ContentRepository,
        mock_gemini_client: MagicMock,
        test_content: Content,
        cleanup_content: None,
    ) -> None:
        """_handle_process_task 핸들러 테스트."""
        with (
            patch("src.services.content_pipeline.translate_content") as mock_translate,
            patch("src.services.content_pipeline.summarize_content") as mock_summarize,
            patch("src.services.content_pipeline.score_relevance") as mock_score,
        ):
            mock_translate.return_value = MagicMock(
                title_ko="테스트 제목",
                body_ko="테스트 본문",
            )
            mock_summarize.return_value = MagicMock(
                title_ko="요약 제목",
                summary_ko="요약 내용입니다.",
                why_important="중요한 이유",
                categories=["테스트"],
            )
            mock_score.return_value = MagicMock(score=0.75)

            # TasksClient mock으로 핸들러 테스트
            mock_tasks = MagicMock()

            pipeline = ContentPipeline(
                source_repo=source_repo,
                content_repo=content_repo,
                gemini_client=mock_gemini_client,
                tasks_client=mock_tasks,
            )

            # 핸들러 직접 호출
            pipeline._handle_process_task({"content_id": test_content.id})

            # Firestore 확인
            updated_content = content_repo.get_by_id(test_content.id)
            assert updated_content is not None
            assert updated_content.processing_status == ProcessingStatus.COMPLETED
            assert updated_content.relevance_score == 0.75

    def test_handle_process_task_content_not_found(
        self,
        source_repo: SourceRepository,
        content_repo: ContentRepository,
        mock_gemini_client: MagicMock,
    ) -> None:
        """존재하지 않는 콘텐츠 처리 시도."""
        mock_tasks = MagicMock()

        pipeline = ContentPipeline(
            source_repo=source_repo,
            content_repo=content_repo,
            gemini_client=mock_gemini_client,
            tasks_client=mock_tasks,
        )

        with pytest.raises(ValueError, match="Content not found"):
            pipeline._handle_process_task({"content_id": "cnt_nonexistent_999"})

    def test_process_multiple_contents_batch(
        self,
        source_repo: SourceRepository,
        content_repo: ContentRepository,
        mock_gemini_client: MagicMock,
    ) -> None:
        """여러 콘텐츠 배치 처리."""
        now = datetime.now(UTC)

        # 3개의 테스트 콘텐츠 생성
        contents = []
        for i in range(3):
            content = Content(
                id=f"cnt_batch_{uuid.uuid4().hex[:8]}",
                source_id="src_batch_001",
                content_key=f"src_batch_001:{uuid.uuid4().hex[:16]}",
                original_url=f"https://test.example.com/batch-article-{i}",
                original_title=f"Batch Test Article {i}",
                original_body=f"This is batch test content number {i}.",
                original_language="en",
                processing_status=ProcessingStatus.PENDING,
                collected_at=now,
            )
            content_repo.create(content)
            contents.append(content)

        try:
            with (
                patch(
                    "src.services.content_pipeline.translate_content"
                ) as mock_translate,
                patch(
                    "src.services.content_pipeline.summarize_content"
                ) as mock_summarize,
                patch("src.services.content_pipeline.score_relevance") as mock_score,
            ):
                mock_translate.return_value = MagicMock(
                    title_ko="배치 테스트",
                    body_ko="배치 테스트 내용",
                )
                mock_summarize.return_value = MagicMock(
                    title_ko="배치 요약",
                    summary_ko="배치 요약 내용",
                    why_important="배치 중요성",
                    categories=["테스트"],
                )
                mock_score.return_value = MagicMock(score=0.80)

                pipeline = ContentPipeline(
                    source_repo=source_repo,
                    content_repo=content_repo,
                    gemini_client=mock_gemini_client,
                )

                # 각 콘텐츠 처리
                success_count = 0
                for content in contents:
                    if pipeline._process_single_content(content):
                        success_count += 1

                # 모두 성공 확인
                assert success_count == 3

                # Firestore에서 모두 처리 완료 확인
                for content in contents:
                    updated = content_repo.get_by_id(content.id)
                    assert updated is not None
                    assert updated.processing_status == ProcessingStatus.COMPLETED

        finally:
            # 정리
            for content in contents:
                try:
                    content_repo.delete(content.id)
                except Exception:
                    pass

    def test_process_preserves_original_data(
        self,
        source_repo: SourceRepository,
        content_repo: ContentRepository,
        mock_gemini_client: MagicMock,
        test_content: Content,
        cleanup_content: None,
    ) -> None:
        """처리 후에도 원본 데이터가 보존됨."""
        original_title = test_content.original_title
        original_body = test_content.original_body
        original_url = test_content.original_url

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
                why_important="중요성",
                categories=["AI"],
            )
            mock_score.return_value = MagicMock(score=0.85)

            pipeline = ContentPipeline(
                source_repo=source_repo,
                content_repo=content_repo,
                gemini_client=mock_gemini_client,
            )

            pipeline._process_single_content(test_content)

            # 원본 데이터 보존 확인
            updated_content = content_repo.get_by_id(test_content.id)
            assert updated_content is not None
            assert updated_content.original_title == original_title
            assert updated_content.original_body == original_body
            assert updated_content.original_url == original_url

            # 처리된 데이터도 존재
            assert updated_content.title_ko is not None
            assert updated_content.summary_ko is not None
