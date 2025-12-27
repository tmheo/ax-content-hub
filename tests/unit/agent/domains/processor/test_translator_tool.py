"""Tests for translator tool."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.agent.domains.processor.tools.translator_tool import (
    TranslationResult,
    translate_content,
)
from src.models.content import Content, ProcessingStatus


class TestTranslateContent:
    """Tests for translate_content function."""

    @pytest.fixture
    def sample_content(self) -> Content:
        """샘플 콘텐츠."""
        return Content(
            id="cnt_test123",
            source_id="src_001",
            content_key="src_001:abc123",
            original_url="https://example.com/article",
            original_title="GPT-5 Released with Major Reasoning Improvements",
            original_body="OpenAI has announced GPT-5, featuring significant improvements in reasoning capabilities.",
            original_language="en",
            processing_status=ProcessingStatus.PENDING,
            collected_at=datetime.now(UTC),
        )

    @pytest.fixture
    def mock_gemini_client(self) -> MagicMock:
        """Mock GeminiClient."""
        return MagicMock()

    def test_translate_title_and_body(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """제목과 본문 번역."""
        mock_gemini_client.translate.side_effect = [
            "GPT-5 출시: 추론 능력 대폭 향상",
            "OpenAI가 GPT-5를 발표했습니다. 추론 능력이 크게 향상되었습니다.",
        ]

        result = translate_content(
            content=sample_content,
            gemini_client=mock_gemini_client,
            target_lang="ko",
        )

        assert result.title_ko == "GPT-5 출시: 추론 능력 대폭 향상"
        assert "GPT-5를 발표" in result.body_ko
        assert mock_gemini_client.translate.call_count == 2

    def test_translate_with_source_language(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """원본 언어 지정."""
        mock_gemini_client.translate.return_value = "번역된 텍스트"

        translate_content(
            content=sample_content,
            gemini_client=mock_gemini_client,
            target_lang="ko",
        )

        # 원본 언어가 전달되어야 함
        calls = mock_gemini_client.translate.call_args_list
        assert calls[0][1]["source_lang"] == "en"

    def test_translate_korean_content_skips(
        self,
        mock_gemini_client: MagicMock,
    ) -> None:
        """한국어 콘텐츠는 번역 건너뜀."""
        korean_content = Content(
            id="cnt_test123",
            source_id="src_001",
            content_key="src_001:abc123",
            original_url="https://example.com/article",
            original_title="GPT-5 출시: 추론 능력 대폭 향상",
            original_body="OpenAI가 GPT-5를 발표했습니다.",
            original_language="ko",
            processing_status=ProcessingStatus.PENDING,
            collected_at=datetime.now(UTC),
        )

        result = translate_content(
            content=korean_content,
            gemini_client=mock_gemini_client,
            target_lang="ko",
        )

        # 번역 호출 없이 원본 사용
        mock_gemini_client.translate.assert_not_called()
        assert result.title_ko == korean_content.original_title
        assert result.body_ko == korean_content.original_body

    def test_translate_empty_body(
        self,
        mock_gemini_client: MagicMock,
    ) -> None:
        """본문 없는 경우."""
        content = Content(
            id="cnt_test123",
            source_id="src_001",
            content_key="src_001:abc123",
            original_url="https://example.com/article",
            original_title="Title Only Article",
            original_body=None,
            original_language="en",
            processing_status=ProcessingStatus.PENDING,
            collected_at=datetime.now(UTC),
        )

        mock_gemini_client.translate.return_value = "제목만 있는 글"

        result = translate_content(
            content=content,
            gemini_client=mock_gemini_client,
            target_lang="ko",
        )

        # 제목만 번역
        assert mock_gemini_client.translate.call_count == 1
        assert result.title_ko == "제목만 있는 글"
        assert result.body_ko is None

    def test_translate_result_structure(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """TranslationResult 구조 확인."""
        mock_gemini_client.translate.side_effect = [
            "번역된 제목",
            "번역된 본문",
        ]

        result = translate_content(
            content=sample_content,
            gemini_client=mock_gemini_client,
            target_lang="ko",
        )

        assert isinstance(result, TranslationResult)
        assert hasattr(result, "title_ko")
        assert hasattr(result, "body_ko")
        assert hasattr(result, "source_language")
        assert hasattr(result, "target_language")

    def test_translate_preserves_languages(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """언어 정보 보존."""
        mock_gemini_client.translate.side_effect = ["제목", "본문"]

        result = translate_content(
            content=sample_content,
            gemini_client=mock_gemini_client,
            target_lang="ko",
        )

        assert result.source_language == "en"
        assert result.target_language == "ko"

    def test_translate_long_body_truncates(
        self,
        mock_gemini_client: MagicMock,
    ) -> None:
        """긴 본문 자동 잘라내기."""
        long_body = "A" * 50000  # 50k 문자
        content = Content(
            id="cnt_test123",
            source_id="src_001",
            content_key="src_001:abc123",
            original_url="https://example.com/article",
            original_title="Long Article",
            original_body=long_body,
            original_language="en",
            processing_status=ProcessingStatus.PENDING,
            collected_at=datetime.now(UTC),
        )

        mock_gemini_client.translate.side_effect = ["긴 글", "번역된 본문"]

        translate_content(
            content=content,
            gemini_client=mock_gemini_client,
            target_lang="ko",
        )

        # translate 호출 시 본문이 잘렸는지 확인
        calls = mock_gemini_client.translate.call_args_list
        body_call = calls[1]
        translated_text = body_call[1]["text"]
        assert len(translated_text) <= 30000  # 최대 30k로 제한

    def test_translate_error_handling(
        self,
        sample_content: Content,
        mock_gemini_client: MagicMock,
    ) -> None:
        """번역 에러 처리."""
        mock_gemini_client.translate.side_effect = Exception("API Error")

        with pytest.raises(Exception) as exc_info:
            translate_content(
                content=sample_content,
                gemini_client=mock_gemini_client,
                target_lang="ko",
            )

        assert "API Error" in str(exc_info.value)
