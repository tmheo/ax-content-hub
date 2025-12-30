# Data Model: Phase 2 콘텐츠 수집 확장

**Date**: 2025-12-30
**Feature Branch**: `003-phase2-collection-expansion`

## Overview

Phase 2에서 추가/수정되는 데이터 모델을 정의합니다.

---

## 1. Source 모델 확장

### 변경 사항

`SourceType` Enum에 `WEB` 타입 추가

```python
# src/models/source.py

class SourceType(str, Enum):
    """소스 타입."""
    RSS = "rss"
    YOUTUBE = "youtube"
    WEB = "web"  # 신규 추가
```

### WEB 타입 config 스키마

```python
# WEB 타입 Source.config 예시
{
    "selector": ".blog-post",       # 콘텐츠 목록/본문 CSS selector
    "wait_for": ".blog-list",       # JS 로딩 대기 selector (optional)
    "url_pattern": "/blog/\\d{4}/", # 콘텐츠 URL 패턴 (optional, regex)
    "timeout_seconds": 30,          # 페이지별 타임아웃 (optional, default: 30)
}
```

### 검증 규칙

| 필드 | 타입 | 필수 | 검증 |
|------|------|------|------|
| selector | str | N | CSS selector 형식 |
| wait_for | str | N | CSS selector 형식 |
| url_pattern | str | N | 유효한 정규식 |
| timeout_seconds | int | N | 1-120 범위 |

---

## 2. 신규 값 객체 (Value Objects)

### 2.1 WebScraperConfig

웹 스크래핑 설정을 담는 값 객체

```python
# src/agent/domains/collector/tools/web_scraper_tool.py

from dataclasses import dataclass

@dataclass(frozen=True)
class WebScraperConfig:
    """웹 스크래핑 설정."""

    selector: str | None = None
    """콘텐츠 추출 CSS selector"""

    wait_for: str | None = None
    """JS 로딩 대기 selector"""

    url_pattern: str | None = None
    """콘텐츠 URL 패턴 (정규식)"""

    timeout_seconds: int = 30
    """페이지별 타임아웃 (초)"""

    @classmethod
    def from_source_config(cls, config: dict) -> "WebScraperConfig":
        """Source.config에서 생성"""
        return cls(
            selector=config.get("selector"),
            wait_for=config.get("wait_for"),
            url_pattern=config.get("url_pattern"),
            timeout_seconds=config.get("timeout_seconds", 30),
        )
```

### 2.2 ScrapedContent

웹 스크래핑 결과를 담는 값 객체

```python
@dataclass(frozen=True)
class ScrapedContent:
    """스크래핑된 콘텐츠 결과."""

    url: str
    """콘텐츠 URL"""

    title: str
    """콘텐츠 제목"""

    body: str
    """콘텐츠 본문"""

    published_at: datetime | None = None
    """발행일 (파싱 가능한 경우)"""

    extraction_stage: int = 0
    """추출된 폴백 단계 (1-4)"""

    def is_valid(self, min_body_length: int = 200) -> bool:
        """유효한 콘텐츠인지 확인"""
        return bool(self.title) and len(self.body) >= min_body_length
```

### 2.3 TranscriptionResult

YouTube STT 결과를 담는 값 객체

```python
# src/agent/domains/collector/tools/youtube_stt.py

@dataclass(frozen=True)
class TranscriptionResult:
    """음성 인식 결과."""

    text: str
    """전사된 텍스트"""

    language: str
    """감지된 언어 코드"""

    language_probability: float
    """언어 감지 확률 (0.0-1.0)"""

    duration_seconds: float
    """오디오 길이 (초)"""
```

---

## 3. Settings 확장

### 신규 설정 필드

```python
# src/config/settings.py

class Settings(BaseSettings):
    # ... 기존 설정 ...

    # -------------------------------------------------------------------------
    # Web Scraping (Phase 2)
    # -------------------------------------------------------------------------
    SCRAPING_TIMEOUT_SECONDS: int = 60
    """웹 스크래핑 총 타임아웃"""

    SCRAPING_MIN_CONTENT_LENGTH: int = 200
    """최소 콘텐츠 길이 (자)"""

    SCRAPING_REQUEST_INTERVAL_MIN: float = 2.0
    """최소 요청 간격 (초)"""

    SCRAPING_REQUEST_INTERVAL_MAX: float = 5.0
    """최대 요청 간격 (초)"""

    # -------------------------------------------------------------------------
    # YouTube STT (Phase 2)
    # -------------------------------------------------------------------------
    STT_ENABLED: bool = True
    """STT 폴백 활성화 여부"""

    STT_MODEL_SIZE: str = "small"
    """Whisper 모델 크기 (tiny, base, small, medium)"""

    STT_COMPUTE_TYPE: str = "int8"
    """연산 타입 (int8, float16, float32)"""

    STT_MAX_VIDEO_DURATION_MINUTES: int = 30
    """STT 대상 최대 영상 길이 (분)"""

    # -------------------------------------------------------------------------
    # Quality Filtering (Phase 2)
    # -------------------------------------------------------------------------
    QUALITY_SIMILARITY_THRESHOLD: float = 0.85
    """중복 판단 유사도 임계값"""

    QUALITY_MAX_AGE_DAYS: int = 7
    """최신성 필터 기준일"""

    QUALITY_MIN_BODY_LENGTH: int = 100
    """최소 본문 길이 (자)"""

    QUALITY_REQUIRE_TITLE: bool = True
    """제목 필수 여부"""
```

---

## 4. QualityFilter 확장

### 신규 메서드

```python
# src/services/quality_filter.py

class QualityFilter:
    # ... 기존 메서드 유지 ...

    def filter_duplicates(
        self,
        contents: list[Content],
        similarity_threshold: float = 0.85,
    ) -> list[Content]:
        """제목 유사도 기반 중복 제거.

        Args:
            contents: 필터링할 콘텐츠 목록
            similarity_threshold: 유사도 임계값 (0.0~1.0)

        Returns:
            중복 제거된 콘텐츠 목록 (최신 우선)
        """

    def filter_by_recency(
        self,
        contents: list[Content],
        max_age_days: int = 7,
    ) -> list[Content]:
        """최신성 기준 필터링.

        Args:
            contents: 필터링할 콘텐츠 목록
            max_age_days: 최대 일수

        Returns:
            N일 이내 콘텐츠만 포함된 목록
        """

    def filter_by_quality(
        self,
        contents: list[Content],
        min_body_length: int = 100,
        require_title: bool = True,
    ) -> list[Content]:
        """콘텐츠 품질 필터링.

        Args:
            contents: 필터링할 콘텐츠 목록
            min_body_length: 최소 본문 길이
            require_title: 제목 필수 여부

        Returns:
            품질 기준 통과 콘텐츠 목록
        """

    def apply_all_filters(
        self,
        contents: list[Content],
        min_relevance: float | None = None,
        max_age_days: int | None = None,
        remove_duplicates: bool = True,
        similarity_threshold: float = 0.85,
        min_body_length: int = 100,
        require_title: bool = True,
        status: ProcessingStatus | None = None,
        categories: list[str] | None = None,
        sort_by: str = "relevance",
        limit: int | None = None,
    ) -> list[Content]:
        """모든 필터 조합 적용.

        Args:
            contents: 필터링할 콘텐츠 목록
            min_relevance: 최소 관련성 점수
            max_age_days: 최대 일수
            remove_duplicates: 중복 제거 여부
            similarity_threshold: 유사도 임계값
            min_body_length: 최소 본문 길이
            require_title: 제목 필수 여부
            status: 처리 상태 필터
            categories: 카테고리 필터
            sort_by: 정렬 기준 ("relevance", "recency")
            limit: 결과 개수 제한

        Returns:
            필터링된 콘텐츠 목록
        """
```

### 유사도 계산 (private 메서드)

```python
def _calculate_similarity(self, text_a: str, text_b: str) -> float:
    """Jaccard 유사도 계산.

    Args:
        text_a: 첫 번째 텍스트
        text_b: 두 번째 텍스트

    Returns:
        유사도 (0.0~1.0)
    """
    tokens_a = self._tokenize(text_a)
    tokens_b = self._tokenize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)

    return intersection / union

def _tokenize(self, text: str) -> set[str]:
    """유사도 비교용 토큰화.

    Args:
        text: 토큰화할 텍스트

    Returns:
        토큰 집합
    """
    tokens = set(text.lower().split())
    return {t for t in tokens if len(t) > 1}
```

---

## 5. 상태 전이 (State Transitions)

### Content 처리 상태

```
                     ┌─────────────────────────────────────────────┐
                     │                                             │
                     ▼                                             │
┌─────────┐    ┌────────────┐    ┌───────────┐    ┌───────────┐   │
│ PENDING │───▶│ PROCESSING │───▶│ COMPLETED │    │  SKIPPED  │   │
└─────────┘    └────────────┘    └───────────┘    └───────────┘   │
     │              │                                   ▲          │
     │              │                                   │          │
     │              └───────────────────────────────────┤          │
     │                      (자막 없음, 길이 초과)         │          │
     │                                                  │          │
     └──────────────────────────────────────────────────┘          │
            (중복 콘텐츠)                                            │
                                                                   │
                     ┌──────────┐                                  │
                     │  FAILED  │◀─────────────────────────────────┘
                     └──────────┘    (처리 실패, 재시도 초과)
                          │
                          ▼
                     ┌──────────┐
                     │ TIMEOUT  │
                     └──────────┘    (타임아웃)
```

### 새로운 SKIPPED 케이스

| 케이스 | 조건 | 처리 |
|--------|------|------|
| 자막 없음 + STT 비활성화 | transcript=None, STT_ENABLED=False | status=SKIPPED |
| 영상 길이 초과 | duration > STT_MAX_VIDEO_DURATION_MINUTES | status=SKIPPED |
| 중복 콘텐츠 | similarity >= threshold | 저장하지 않음 (건너뜀) |

---

## 6. 관계 다이어그램

```
┌──────────────────────────────────────────────────────────────────┐
│                           Source                                  │
├──────────────────────────────────────────────────────────────────┤
│ id: str                                                          │
│ type: SourceType  (RSS | YOUTUBE | WEB)                          │
│ url: HttpUrl                                                     │
│ config: dict  ─────────────────────────┐                         │
└───────────────────────────────────────┬┘                         │
                                        │                          │
                                        ▼                          │
                              ┌────────────────────┐               │
                              │ WebScraperConfig   │ (WEB 타입용)   │
                              ├────────────────────┤               │
                              │ selector: str?     │               │
                              │ wait_for: str?     │               │
                              │ url_pattern: str?  │               │
                              │ timeout_seconds: int│              │
                              └────────────────────┘               │
                                                                   │
┌──────────────────────────────────────────────────────────────────┐
│                           Content                                 │
├──────────────────────────────────────────────────────────────────┤
│ id: str                                                          │
│ source_id: str  ─────────────────────────────────────────────────┼──▶ Source.id
│ content_key: str  (중복 방지용)                                    │
│ original_url: str                                                │
│ original_title: str                                              │
│ original_body: str?  (RSS: 요약, YouTube: 자막, WEB: 본문)        │
│ processing_status: ProcessingStatus                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 7. 마이그레이션 고려사항

### 기존 데이터 호환성

- `SourceType` Enum 확장은 하위 호환 유지
- 기존 RSS, YOUTUBE 타입 데이터 영향 없음
- `Settings` 신규 필드는 모두 기본값 제공

### Firestore 인덱스

WEB 타입 필터링을 위한 인덱스 추가 불필요 (기존 `type` 필드 인덱스 활용)
