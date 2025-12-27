"""Tests for summarizer tool."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.agent.domains.processor.tools.summarizer_tool import (
    SummaryResult,
    summarize_content,
)
from src.models.content import Content, ProcessingStatus


class TestSummarizeContent:
    """Tests for summarize_content function."""

    @pytest.fixture
    def sample_content(self) -> Content:
        """샘플 콘텐츠."""
        return Content(
            id="cnt_test123",
            source_id="src_001",
            content_key="src_001:abc123",
            original_url="https://example.com/article",
            original_title="GPT-5 Released",
            original_body="OpenAI has announced GPT-5 with major reasoning improvements.",
            original_language="en",
            processing_status=ProcessingStatus.PENDING,
            collected_at=datetime.now(UTC),
        )

    @pytest.fixture
    def mock_gemini_client(self) -> MagicMock:
        """Mock GeminiClient."""
        return MagicMock()

    def test_summarize_returns_geeknews_style(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """GeekNews 스타일 요약 생성."""
        mock_gemini_client.generate_json.return_value = {
            "title_ko": "GPT-5 출시: 추론 향상",
            "summary_ko": "OpenAI가 GPT-5를 발표했습니다. 추론 능력이 크게 향상되었습니다. 기업 AI 도입에 영향을 줄 것입니다.",
            "why_important": "AX 전략에서 LLM 활용 방안에 직접적인 영향을 미칩니다.",
        }

        result = summarize_content(
            content=sample_content,
            title_ko="GPT-5 출시: 추론 능력 대폭 향상",
            body_ko="OpenAI가 GPT-5를 발표했습니다. 추론 능력이 크게 향상되었습니다.",
            gemini_client=mock_gemini_client,
        )

        assert isinstance(result, SummaryResult)
        assert len(result.title_ko) <= 20
        assert result.summary_ko
        assert result.why_important

    def test_summarize_title_max_20_chars(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """제목 최대 20자 제한."""
        mock_gemini_client.generate_json.return_value = {
            "title_ko": "매우 긴 제목인데 이것은 20자를 초과합니다",
            "summary_ko": "요약 내용",
            "why_important": "중요성",
        }

        result = summarize_content(
            content=sample_content,
            title_ko="번역된 제목",
            body_ko="번역된 본문",
            gemini_client=mock_gemini_client,
        )

        # 자동으로 20자 잘라내기
        assert len(result.title_ko) <= 20

    def test_summarize_3_sentences_max(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """요약 최대 3문장."""
        mock_gemini_client.generate_json.return_value = {
            "title_ko": "짧은 제목",
            "summary_ko": "첫 번째. 두 번째. 세 번째. 네 번째. 다섯 번째.",
            "why_important": "중요성",
        }

        result = summarize_content(
            content=sample_content,
            title_ko="번역된 제목",
            body_ko="번역된 본문",
            gemini_client=mock_gemini_client,
        )

        # 문장 수 확인 (마침표 기준)
        sentences = [s.strip() for s in result.summary_ko.split(".") if s.strip()]
        assert len(sentences) <= 3

    def test_summarize_includes_why_important(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """why_important 필드 포함."""
        mock_gemini_client.generate_json.return_value = {
            "title_ko": "짧은 제목",
            "summary_ko": "요약 내용입니다.",
            "why_important": "AX 전략에 중요한 트렌드입니다.",
        }

        result = summarize_content(
            content=sample_content,
            title_ko="번역된 제목",
            body_ko="번역된 본문",
            gemini_client=mock_gemini_client,
        )

        assert result.why_important == "AX 전략에 중요한 트렌드입니다."

    def test_summarize_uses_translated_content(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """번역된 콘텐츠 사용."""
        mock_gemini_client.generate_json.return_value = {
            "title_ko": "요약 제목",
            "summary_ko": "요약 내용",
            "why_important": "중요성",
        }

        summarize_content(
            content=sample_content,
            title_ko="번역된 제목",
            body_ko="번역된 본문",
            gemini_client=mock_gemini_client,
        )

        # generate_json 호출 확인
        call_args = mock_gemini_client.generate_json.call_args
        prompt = call_args[1]["prompt"]
        assert "번역된 제목" in prompt
        assert "번역된 본문" in prompt

    def test_summarize_with_retry_on_json_error(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """JSON 파싱 실패 시 재시도."""
        # 첫 번째 호출은 실패, 두 번째 성공
        mock_gemini_client.generate_json.side_effect = [
            ValueError("Invalid JSON"),
            {
                "title_ko": "재시도 제목",
                "summary_ko": "재시도 요약",
                "why_important": "재시도 중요성",
            },
        ]

        result = summarize_content(
            content=sample_content,
            title_ko="번역된 제목",
            body_ko="번역된 본문",
            gemini_client=mock_gemini_client,
            max_retries=2,
        )

        assert result.title_ko == "재시도 제목"
        assert mock_gemini_client.generate_json.call_count == 2

    def test_summarize_raises_after_max_retries(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """최대 재시도 후 예외 발생."""
        mock_gemini_client.generate_json.side_effect = ValueError("Invalid JSON")

        with pytest.raises(ValueError) as exc_info:
            summarize_content(
                content=sample_content,
                title_ko="번역된 제목",
                body_ko="번역된 본문",
                gemini_client=mock_gemini_client,
                max_retries=2,
            )

        assert "Failed to summarize" in str(exc_info.value)

    def test_summarize_empty_body(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """본문 없는 경우."""
        mock_gemini_client.generate_json.return_value = {
            "title_ko": "제목만 요약",
            "summary_ko": "제목 기반 요약입니다.",
            "why_important": "중요성",
        }

        result = summarize_content(
            content=sample_content,
            title_ko="번역된 제목",
            body_ko=None,
            gemini_client=mock_gemini_client,
        )

        assert result.title_ko
        assert result.summary_ko

    def test_summarize_categories_extraction(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """카테고리 추출."""
        mock_gemini_client.generate_json.return_value = {
            "title_ko": "짧은 제목",
            "summary_ko": "요약 내용입니다.",
            "why_important": "중요성",
            "categories": ["LLM", "Enterprise AI", "Product Launch"],
        }

        result = summarize_content(
            content=sample_content,
            title_ko="번역된 제목",
            body_ko="번역된 본문",
            gemini_client=mock_gemini_client,
        )

        assert result.categories == ["LLM", "Enterprise AI", "Product Launch"]

    def test_summarize_default_categories(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """카테고리 없을 때 빈 리스트."""
        mock_gemini_client.generate_json.return_value = {
            "title_ko": "짧은 제목",
            "summary_ko": "요약 내용입니다.",
            "why_important": "중요성",
        }

        result = summarize_content(
            content=sample_content,
            title_ko="번역된 제목",
            body_ko="번역된 본문",
            gemini_client=mock_gemini_client,
        )

        assert result.categories == []
