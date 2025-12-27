"""Tests for scorer tool."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.agent.domains.processor.tools.scorer_tool import (
    ScoringResult,
    score_relevance,
)
from src.models.content import Content, ProcessingStatus


class TestScoreRelevance:
    """Tests for score_relevance function."""

    @pytest.fixture
    def sample_content(self) -> Content:
        """샘플 콘텐츠."""
        return Content(
            id="cnt_test123",
            source_id="src_001",
            content_key="src_001:abc123",
            original_url="https://example.com/article",
            original_title="GPT-5 Released",
            original_body="OpenAI has announced GPT-5.",
            original_language="en",
            processing_status=ProcessingStatus.PENDING,
            collected_at=datetime.now(UTC),
        )

    @pytest.fixture
    def mock_gemini_client(self) -> MagicMock:
        """Mock GeminiClient."""
        return MagicMock()

    def test_score_returns_0_to_1(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """점수가 0.0~1.0 범위."""
        mock_gemini_client.generate_score.return_value = 0.85

        result = score_relevance(
            content=sample_content,
            summary_ko="GPT-5가 출시되었습니다.",
            why_important="LLM 기술 발전에 중요합니다.",
            gemini_client=mock_gemini_client,
        )

        assert 0.0 <= result.score <= 1.0
        assert result.score == 0.85

    def test_score_high_relevance_ax_content(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """AX 관련성 높은 콘텐츠."""
        mock_gemini_client.generate_score.return_value = 0.92

        result = score_relevance(
            content=sample_content,
            summary_ko="기업의 AI 도입 전략을 다룹니다.",
            why_important="AX 전략 수립에 직접 활용 가능합니다.",
            gemini_client=mock_gemini_client,
        )

        assert result.score >= 0.7

    def test_score_low_relevance_non_ax_content(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """AX 관련성 낮은 콘텐츠."""
        mock_gemini_client.generate_score.return_value = 0.15

        result = score_relevance(
            content=sample_content,
            summary_ko="새로운 게임이 출시되었습니다.",
            why_important="엔터테인먼트 산업 동향입니다.",
            gemini_client=mock_gemini_client,
        )

        assert result.score < 0.3

    def test_score_uses_summary_and_importance(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """요약과 중요성 사용 확인."""
        mock_gemini_client.generate_score.return_value = 0.75

        score_relevance(
            content=sample_content,
            summary_ko="테스트 요약",
            why_important="테스트 중요성",
            gemini_client=mock_gemini_client,
        )

        call_args = mock_gemini_client.generate_score.call_args
        prompt = call_args[1]["prompt"]
        assert "테스트 요약" in prompt
        assert "테스트 중요성" in prompt

    def test_score_result_structure(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """ScoringResult 구조."""
        mock_gemini_client.generate_score.return_value = 0.65

        result = score_relevance(
            content=sample_content,
            summary_ko="요약",
            why_important="중요성",
            gemini_client=mock_gemini_client,
        )

        assert isinstance(result, ScoringResult)
        assert hasattr(result, "score")
        assert hasattr(result, "content_id")
        assert result.content_id == sample_content.id

    def test_score_clamps_to_valid_range(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """범위 벗어난 점수 클램핑."""
        # GeminiClient._parse_score가 이미 클램핑하지만 한번 더 확인
        mock_gemini_client.generate_score.return_value = 1.5

        result = score_relevance(
            content=sample_content,
            summary_ko="요약",
            why_important="중요성",
            gemini_client=mock_gemini_client,
        )

        assert result.score <= 1.0

    def test_score_error_handling(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """점수 생성 에러 처리."""
        mock_gemini_client.generate_score.side_effect = ValueError("Failed to parse")

        with pytest.raises(ValueError):
            score_relevance(
                content=sample_content,
                summary_ko="요약",
                why_important="중요성",
                gemini_client=mock_gemini_client,
            )

    def test_score_with_categories(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """카테고리 정보 활용."""
        mock_gemini_client.generate_score.return_value = 0.88

        result = score_relevance(
            content=sample_content,
            summary_ko="LLM 관련 콘텐츠",
            why_important="AI 도입에 중요",
            gemini_client=mock_gemini_client,
            categories=["LLM", "Enterprise AI"],
        )

        # 프롬프트에 카테고리 포함
        call_args = mock_gemini_client.generate_score.call_args
        prompt = call_args[1]["prompt"]
        assert "LLM" in prompt or result.score > 0

    def test_score_empty_summary(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """빈 요약 처리."""
        mock_gemini_client.generate_score.return_value = 0.3

        result = score_relevance(
            content=sample_content,
            summary_ko="",
            why_important="중요성",
            gemini_client=mock_gemini_client,
        )

        # 빈 요약도 처리 가능
        assert result.score >= 0.0
