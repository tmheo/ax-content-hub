# Tool Interfaces: Phase 2 콘텐츠 수집 확장

**Date**: 2025-12-30
**Feature Branch**: `003-phase2-collection-expansion`

## Overview

Phase 2에서 추가되는 내부 도구(Collector Tools)의 인터페이스를 정의합니다.
이 기능은 신규 REST API를 추가하지 않으며, 기존 내부 엔드포인트(`/internal/tasks/*`)를 통해 호출됩니다.

---

## 1. Web Scraper Tool

### Function Signature

```python
async def fetch_web(
    source_id: str,
    source_url: str,
    content_repo: ContentRepository,
    config: WebScraperConfig | None = None,
) -> list[Content]:
    """웹 페이지에서 콘텐츠 수집 (4단계 폴백).

    Args:
        source_id: 소스 ID (예: "src_web_001")
        source_url: 수집할 URL
        content_repo: 콘텐츠 저장소 인스턴스
        config: 스크래핑 설정 (optional)

    Returns:
        수집된 Content 목록

    Raises:
        ScrapingError: 모든 폴백 전략 실패 시
        TimeoutError: 총 타임아웃 초과 시
    """
```

### Input Schema

```python
@dataclass(frozen=True)
class WebScraperConfig:
    selector: str | None = None
    wait_for: str | None = None
    url_pattern: str | None = None
    timeout_seconds: int = 30
```

### Output Schema

```python
@dataclass(frozen=True)
class ScrapedContent:
    url: str
    title: str
    body: str
    published_at: datetime | None = None
    extraction_stage: int = 0  # 1-4
```

### Error Types

| 에러 | 설명 | HTTP Status (if applicable) |
|------|------|----------------------------|
| `ScrapingError` | 추출 실패 | N/A (내부 도구) |
| `TimeoutError` | 타임아웃 | N/A |
| `NetworkError` | 네트워크 오류 | N/A |

---

## 2. YouTube STT Tool

### Function Signature

```python
async def fetch_youtube_with_stt(
    video_id: str,
    source_id: str,
    video_title: str,
    content_repo: ContentRepository,
    settings: Settings,
    published_at: datetime | None = None,
) -> Content | None:
    """YouTube 영상 자막 수집 (STT 폴백 포함).

    Args:
        video_id: YouTube 영상 ID (11자)
        source_id: 소스 ID
        video_title: 영상 제목
        content_repo: 콘텐츠 저장소
        settings: 앱 설정
        published_at: 발행일 (optional)

    Returns:
        수집된 Content 또는 None (건너뜀)

    Raises:
        YouTubeExtractionError: 오디오 추출 실패
        TranscriptionError: 음성 인식 실패
    """
```

### Fallback Flow

```
1. youtube-transcript-api로 기존 자막 조회
   ├── 성공 → Content 생성 (PENDING)
   └── 실패 (TranscriptsDisabled)
       │
       ▼
2. STT 폴백 (settings.STT_ENABLED=True)
   ├── 영상 길이 확인 (≤ 30분)
   ├── yt-dlp로 오디오 추출
   ├── faster-whisper로 전사
   └── Content 생성 (PENDING)
       │
       ▼
3. 실패 처리
   ├── STT 비활성화 → None (로그 기록)
   ├── 영상 길이 초과 → None (로그 기록)
   └── 추출/전사 실패 → 에러 raise
```

### Output Schema

```python
@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str
    language_probability: float
    duration_seconds: float
```

### Error Types

| 에러 | 설명 |
|------|------|
| `YouTubeExtractionError` | 오디오 추출 실패 |
| `AgeRestrictedError` | 연령 제한 영상 |
| `VideoUnavailableError` | 영상 접근 불가 |
| `TranscriptionError` | 음성 인식 실패 |

---

## 3. Quality Filter Extensions

### New Methods

```python
class QualityFilter:
    def filter_duplicates(
        self,
        contents: list[Content],
        similarity_threshold: float = 0.85,
    ) -> list[Content]: ...

    def filter_by_recency(
        self,
        contents: list[Content],
        max_age_days: int = 7,
    ) -> list[Content]: ...

    def filter_by_quality(
        self,
        contents: list[Content],
        min_body_length: int = 100,
        require_title: bool = True,
    ) -> list[Content]: ...

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
    ) -> list[Content]: ...
```

---

## 4. ContentPipeline 라우팅 확장

### 변경된 라우팅 로직

```python
async def _collect_from_source(self, source: Source) -> list[str]:
    """소스 타입별 수집 라우팅."""
    match source.type:
        case SourceType.RSS:
            return await self._collect_from_rss(source)
        case SourceType.YOUTUBE:
            return await self._collect_from_youtube(source)  # STT 폴백 포함
        case SourceType.WEB:  # 신규
            return await self._collect_from_web(source)
        case _:
            raise ValueError(f"지원하지 않는 소스 타입: {source.type}")
```

---

## 5. 환경 변수 인터페이스

### 신규 환경 변수

| 변수명 | 타입 | 기본값 | 설명 |
|--------|------|--------|------|
| `SCRAPING_TIMEOUT_SECONDS` | int | 60 | 웹 스크래핑 총 타임아웃 |
| `SCRAPING_MIN_CONTENT_LENGTH` | int | 200 | 최소 콘텐츠 길이 |
| `SCRAPING_REQUEST_INTERVAL_MIN` | float | 2.0 | 최소 요청 간격 (초) |
| `SCRAPING_REQUEST_INTERVAL_MAX` | float | 5.0 | 최대 요청 간격 (초) |
| `STT_ENABLED` | bool | True | STT 폴백 활성화 |
| `STT_MODEL_SIZE` | str | "small" | Whisper 모델 크기 |
| `STT_COMPUTE_TYPE` | str | "int8" | 연산 타입 |
| `STT_MAX_VIDEO_DURATION_MINUTES` | int | 30 | 최대 영상 길이 |
| `QUALITY_SIMILARITY_THRESHOLD` | float | 0.85 | 중복 판단 임계값 |
| `QUALITY_MAX_AGE_DAYS` | int | 7 | 최신성 기준일 |
| `QUALITY_MIN_BODY_LENGTH` | int | 100 | 최소 본문 길이 |
| `QUALITY_REQUIRE_TITLE` | bool | True | 제목 필수 여부 |
