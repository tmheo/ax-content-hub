"""Tests for GeminiClient."""

from unittest.mock import MagicMock, patch

import pytest

from src.adapters.gemini_client import GeminiClient


class TestGeminiClient:
    """Tests for GeminiClient."""

    @pytest.fixture
    def mock_genai_client(self) -> MagicMock:
        """Mock google.genai.Client."""
        return MagicMock()

    @pytest.fixture
    def client(self, mock_genai_client: MagicMock) -> GeminiClient:
        """GeminiClient with mock genai.Client."""
        with patch("src.adapters.gemini_client.genai") as mock_genai:
            mock_genai.Client.return_value = mock_genai_client
            return GeminiClient(api_key="test-api-key")

    def test_init_with_api_key(self) -> None:
        """API 키로 초기화."""
        with patch("src.adapters.gemini_client.genai") as mock_genai:
            GeminiClient(api_key="test-api-key")
            mock_genai.Client.assert_called_once_with(api_key="test-api-key")

    def test_init_with_model(self) -> None:
        """모델 지정 초기화."""
        with patch("src.adapters.gemini_client.genai"):
            client = GeminiClient(api_key="test-key", model="gemini-2.0-flash")
            assert client.model == "gemini-2.0-flash"

    def test_default_model(self, client: GeminiClient) -> None:
        """기본 모델은 gemini-2.0-flash-001."""
        assert client.model == "gemini-2.0-flash-001"

    def test_generate_content(
        self, client: GeminiClient, mock_genai_client: MagicMock
    ) -> None:
        """텍스트 생성."""
        mock_response = MagicMock()
        mock_response.text = "Generated response"
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client.generate_content("Test prompt")

        assert result == "Generated response"
        mock_genai_client.models.generate_content.assert_called_once()

    def test_generate_content_with_system_prompt(
        self, client: GeminiClient, mock_genai_client: MagicMock
    ) -> None:
        """시스템 프롬프트와 함께 텍스트 생성."""
        mock_response = MagicMock()
        mock_response.text = "Response with system context"
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client.generate_content(
            prompt="User prompt",
            system_prompt="You are a helpful assistant",
        )

        assert result == "Response with system context"
        call_args = mock_genai_client.models.generate_content.call_args
        assert "config" in call_args.kwargs

    def test_generate_json(
        self, client: GeminiClient, mock_genai_client: MagicMock
    ) -> None:
        """JSON 응답 생성."""
        mock_response = MagicMock()
        mock_response.text = '{"key": "value", "number": 42}'
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client.generate_json("Generate JSON")

        assert result == {"key": "value", "number": 42}

    def test_generate_json_with_markdown_wrapper(
        self, client: GeminiClient, mock_genai_client: MagicMock
    ) -> None:
        """마크다운 래퍼가 있는 JSON 응답 파싱."""
        mock_response = MagicMock()
        mock_response.text = '```json\n{"key": "value"}\n```'
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client.generate_json("Generate JSON")

        assert result == {"key": "value"}

    def test_generate_json_invalid_json(
        self, client: GeminiClient, mock_genai_client: MagicMock
    ) -> None:
        """잘못된 JSON 응답 처리."""
        mock_response = MagicMock()
        mock_response.text = "This is not JSON"
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            client.generate_json("Generate JSON")

        assert "Failed to parse JSON" in str(exc_info.value)

    def test_generate_json_with_retry(
        self, client: GeminiClient, mock_genai_client: MagicMock
    ) -> None:
        """JSON 파싱 재시도."""
        # 첫 번째 호출: 잘못된 JSON
        # 두 번째 호출: 유효한 JSON
        mock_response_invalid = MagicMock()
        mock_response_invalid.text = "Invalid JSON"
        mock_response_valid = MagicMock()
        mock_response_valid.text = '{"valid": true}'

        mock_genai_client.models.generate_content.side_effect = [
            mock_response_invalid,
            mock_response_valid,
        ]

        result = client.generate_json("Generate JSON", max_retries=2)

        assert result == {"valid": True}
        assert mock_genai_client.models.generate_content.call_count == 2

    def test_generate_json_max_retries_exceeded(
        self, client: GeminiClient, mock_genai_client: MagicMock
    ) -> None:
        """최대 재시도 횟수 초과."""
        mock_response = MagicMock()
        mock_response.text = "Always invalid"
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            client.generate_json("Generate JSON", max_retries=3)

        assert "Failed to parse JSON" in str(exc_info.value)
        assert mock_genai_client.models.generate_content.call_count == 3

    def test_generate_score(
        self, client: GeminiClient, mock_genai_client: MagicMock
    ) -> None:
        """점수(float) 응답 생성."""
        mock_response = MagicMock()
        mock_response.text = "0.85"
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client.generate_score("Rate this content")

        assert result == 0.85

    def test_generate_score_with_explanation(
        self, client: GeminiClient, mock_genai_client: MagicMock
    ) -> None:
        """설명이 포함된 점수 응답 파싱."""
        mock_response = MagicMock()
        mock_response.text = "The relevance score is 0.75 based on..."
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client.generate_score("Rate this content")

        assert result == 0.75

    def test_generate_score_out_of_range(
        self, client: GeminiClient, mock_genai_client: MagicMock
    ) -> None:
        """범위 밖 점수 클램핑."""
        mock_response = MagicMock()
        mock_response.text = "1.5"
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client.generate_score("Rate this content")

        assert result == 1.0  # 최대값으로 클램핑

    def test_generate_score_negative(
        self, client: GeminiClient, mock_genai_client: MagicMock
    ) -> None:
        """음수 점수 클램핑."""
        mock_response = MagicMock()
        mock_response.text = "-0.5"
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client.generate_score("Rate this content")

        assert result == 0.0  # 최소값으로 클램핑

    def test_generate_score_invalid_format(
        self, client: GeminiClient, mock_genai_client: MagicMock
    ) -> None:
        """잘못된 점수 형식."""
        mock_response = MagicMock()
        mock_response.text = "Cannot determine score"
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            client.generate_score("Rate this content")

        assert "Failed to parse score" in str(exc_info.value)

    def test_translate(
        self, client: GeminiClient, mock_genai_client: MagicMock
    ) -> None:
        """텍스트 번역."""
        mock_response = MagicMock()
        mock_response.text = "안녕하세요"
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client.translate("Hello", target_lang="ko")

        assert result == "안녕하세요"
        call_args = mock_genai_client.models.generate_content.call_args
        assert "Korean" in str(call_args) or "ko" in str(call_args)
