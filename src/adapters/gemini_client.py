"""Gemini AI client adapter.

Google Gen AI SDK를 사용한 Gemini API 래퍼.
"""

import json
import re
from typing import Any

from google import genai
from google.genai import types


class GeminiClient:
    """Gemini API 클라이언트.

    google-genai SDK를 사용하여 Gemini 모델과 통신합니다.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash-001",
    ) -> None:
        """Initialize Gemini client.

        Args:
            api_key: Google API 키.
            model: 사용할 Gemini 모델.
        """
        self._client = genai.Client(api_key=api_key)
        self.model = model

    def generate_content(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """텍스트 생성.

        Args:
            prompt: 사용자 프롬프트.
            system_prompt: 시스템 프롬프트 (선택).
            temperature: 생성 온도 (0.0~1.0).

        Returns:
            생성된 텍스트.
        """
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_prompt,
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        return response.text or ""

    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_retries: int = 1,
    ) -> dict[str, Any]:
        """JSON 응답 생성.

        마크다운 래퍼(```json ... ```)를 자동으로 제거합니다.

        Args:
            prompt: 사용자 프롬프트.
            system_prompt: 시스템 프롬프트 (선택).
            max_retries: JSON 파싱 실패 시 재시도 횟수.

        Returns:
            파싱된 JSON dict.

        Raises:
            ValueError: JSON 파싱 실패.
        """
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                # 재시도 시 더 명시적인 지시 추가
                retry_prompt = prompt
                if attempt > 0:
                    retry_prompt = (
                        f"{prompt}\n\n"
                        "IMPORTANT: Respond with valid JSON only. "
                        "Do not include any explanation or markdown."
                    )

                text = self.generate_content(
                    prompt=retry_prompt,
                    system_prompt=system_prompt,
                    temperature=0.3,  # JSON 생성 시 낮은 temperature
                )

                return self._parse_json(text)

            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                continue

        raise ValueError(
            f"Failed to parse JSON after {max_retries} attempts: {last_error}"
        )

    def generate_score(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> float:
        """점수(0.0~1.0) 생성.

        Args:
            prompt: 평가 프롬프트.
            system_prompt: 시스템 프롬프트 (선택).

        Returns:
            0.0~1.0 범위의 점수.

        Raises:
            ValueError: 점수 파싱 실패.
        """
        text = self.generate_content(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,  # 일관된 점수를 위해 낮은 temperature
        )

        return self._parse_score(text)

    def translate(
        self,
        text: str,
        target_lang: str = "ko",
        source_lang: str | None = None,
    ) -> str:
        """텍스트 번역.

        Args:
            text: 번역할 텍스트.
            target_lang: 대상 언어 코드.
            source_lang: 원본 언어 코드 (자동 감지 시 None).

        Returns:
            번역된 텍스트.
        """
        lang_names = {
            "ko": "Korean",
            "en": "English",
            "ja": "Japanese",
            "zh": "Chinese",
        }

        target_name = lang_names.get(target_lang, target_lang)
        source_hint = ""
        if source_lang:
            source_name = lang_names.get(source_lang, source_lang)
            source_hint = f" from {source_name}"

        prompt = (
            f"Translate the following text{source_hint} to {target_name}. "
            "Only provide the translation, without any explanation or notes.\n\n"
            f"Text: {text}"
        )

        return self.generate_content(prompt=prompt, temperature=0.3)

    def _parse_json(self, text: str) -> dict[str, Any]:
        """텍스트에서 JSON 파싱.

        마크다운 코드 블록 래퍼를 자동 제거합니다.

        Args:
            text: 파싱할 텍스트.

        Returns:
            파싱된 dict.

        Raises:
            ValueError: JSON 파싱 실패.
        """
        # 마크다운 코드 블록 제거
        text = text.strip()
        if text.startswith("```"):
            # ```json 또는 ``` 제거
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

    def _parse_score(self, text: str) -> float:
        """텍스트에서 점수 파싱.

        텍스트에서 첫 번째 소수점 숫자를 추출하고 0.0~1.0 범위로 클램핑합니다.

        Args:
            text: 파싱할 텍스트.

        Returns:
            0.0~1.0 범위의 점수.

        Raises:
            ValueError: 점수 파싱 실패.
        """
        # 소수점 숫자 패턴 찾기
        pattern = r"-?\d+\.?\d*"
        matches = re.findall(pattern, text)

        if not matches:
            raise ValueError(f"Failed to parse score from: {text}")

        # 첫 번째 숫자 사용
        score = float(matches[0])

        # 0.0~1.0 범위로 클램핑
        return max(0.0, min(1.0, score))
