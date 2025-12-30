# Phase 2 개발 계획: 콘텐츠 수집 확장

> Phase 1 (MVP 파이프라인) 완료 후, RSS 외 다양한 소스 지원 및 품질 필터링 강화

## 개요

### 목표
- **웹 스크래핑**: Playwright 기반 4단계 폴백 전략으로 RSS 없는 사이트 지원
- **YouTube STT 폴백**: 자막 없는 영상에 대해 yt-dlp + faster-whisper 기반 음성 인식
- **품질 필터링 확장**: 중복/최신성/품질 체크 추가

### 현재 상태 (Phase 1 완료)

| 구성요소 | Phase 1 상태 | Phase 2 목표 |
|---------|------------|-------------|
| Source 모델 | RSS, YouTube만 지원 | WEB 타입 추가 |
| YouTube 수집 | 기존 자막만 | 자막 없으면 STT 폴백 |
| 웹 스크래핑 | 미구현 | Playwright 4단계 폴백 |
| 품질 필터 | 관련성/상태/카테고리 | 중복/최신성/품질 추가 |

---

## 구현 순서

| 순서 | 작업 | 예상 소요 | 우선순위 |
|-----|-----|---------|---------|
| 1 | Source 모델에 WEB 타입 추가 | 0.5일 | P0 |
| 2 | 웹 스크래핑 도구 (4단계 폴백) | 3일 | P1 |
| 3 | YouTube STT 폴백 | 2일 | P1 |
| 4 | 품질 필터링 확장 | 1.5일 | P1 |
| 5 | 통합 테스트 + 마무리 | 1일 | P0 |

---

## 1. Source 모델 WEB 타입 추가

### 수정 파일
- `src/models/source.py`

### 변경 내용

```python
class SourceType(str, Enum):
    """소스 타입."""
    RSS = "rss"
    YOUTUBE = "youtube"
    WEB = "web"  # 추가
```

### Source.config 예시 (WEB 타입)

```python
{
    "id": "src_web_01",
    "name": "AI Blog (No RSS)",
    "type": "web",
    "url": "https://example.com/blog",
    "config": {
        "selector": ".blog-post",       # 목록 페이지의 포스트 selector
        "wait_for": ".blog-list",       # JS 로딩 대기 selector
        "url_pattern": "/blog/\\d{4}/", # 콘텐츠 URL 패턴
    },
}
```

### 테스트
- `tests/unit/models/test_source.py` 확장

---

## 2. 웹 스크래핑 도구 (Playwright 4단계 폴백)

### 신규 파일
- `src/agent/domains/collector/tools/web_scraper_tool.py`
- `tests/unit/agent/domains/collector/test_web_scraper_tool.py`

### 4단계 폴백 전략

```
┌─────────────────────────────────────────────────────────────┐
│  fetch_web(source_url, config)                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1단계: Static + Selector (가장 빠름)                        │
│  ├── httpx로 HTML 가져오기                                  │
│  ├── BeautifulSoup + CSS selector로 추출                    │
│  └── 성공 시 반환, 실패 시 2단계                             │
└─────────────────────────────────────────────────────────────┘
                              │ 실패
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2단계: Dynamic + Selector (JS 렌더링)                       │
│  ├── Playwright로 페이지 로드                               │
│  ├── networkidle 대기                                       │
│  ├── CSS selector로 추출                                    │
│  └── 성공 시 반환, 실패 시 3단계                             │
└─────────────────────────────────────────────────────────────┘
                              │ 실패
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3단계: Structural (위치 기반)                               │
│  ├── 메인 콘텐츠 영역 휴리스틱 탐지                          │
│  │   (article, main, .content, .post 등)                    │
│  ├── 텍스트 밀도 분석으로 본문 추출                          │
│  └── 성공 시 반환, 실패 시 4단계                             │
└─────────────────────────────────────────────────────────────┘
                              │ 실패
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4단계: URL-based (링크 패턴 분석)                           │
│  ├── 페이지 내 링크 수집                                    │
│  ├── 날짜/제목 패턴 분석으로 콘텐츠 링크 식별                 │
│  └── 각 링크에서 콘텐츠 추출                                 │
└─────────────────────────────────────────────────────────────┘
```

### 핵심 구현

```python
# src/agent/domains/collector/tools/web_scraper_tool.py

from dataclasses import dataclass
from datetime import datetime
from playwright.async_api import async_playwright, Page
import httpx
from bs4 import BeautifulSoup

@dataclass
class WebScraperConfig:
    """웹 스크래핑 설정."""
    selector: str | None = None      # CSS selector
    url_pattern: str | None = None   # 링크 패턴 (정규식)
    wait_for: str | None = None      # JS 대기 selector
    timeout_ms: int = 30000          # 타임아웃

@dataclass
class ScrapedContent:
    """스크래핑된 콘텐츠."""
    url: str
    title: str
    body: str
    published_at: datetime | None = None
    extraction_stage: int = 0  # 어느 단계에서 추출되었는지 (1-4)

async def fetch_web(
    source_id: str,
    source_url: str,
    content_repo: ContentRepository,
    config: WebScraperConfig | None = None,
) -> list[Content]:
    """웹 페이지에서 콘텐츠 수집 (4단계 폴백).

    Args:
        source_id: 소스 ID
        source_url: 수집할 URL
        content_repo: 콘텐츠 저장소
        config: 스크래핑 설정

    Returns:
        수집된 Content 목록
    """
    config = config or WebScraperConfig()

    # 1단계: Static + Selector
    contents = await _extract_static(source_url, config)
    if contents:
        return await _save_contents(source_id, contents, content_repo, stage=1)

    # 2단계 이후: Playwright 사용
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # 2단계: Dynamic + Selector
        contents = await _extract_dynamic(page, source_url, config)
        if contents:
            await browser.close()
            return await _save_contents(source_id, contents, content_repo, stage=2)

        # 3단계: Structural
        contents = await _extract_structural(page)
        if contents:
            await browser.close()
            return await _save_contents(source_id, contents, content_repo, stage=3)

        # 4단계: URL-based
        contents = await _extract_by_links(page, source_url, config)
        await browser.close()
        return await _save_contents(source_id, contents, content_repo, stage=4)
```

### ContentPipeline 수정

```python
# src/services/content_pipeline.py

async def _collect_from_source(self, source: Source) -> list[str]:
    """소스 타입별 수집 라우팅."""
    if source.type == SourceType.RSS:
        return await self._collect_from_rss(source)
    elif source.type == SourceType.YOUTUBE:
        return await self._collect_from_youtube(source)
    elif source.type == SourceType.WEB:  # 신규
        return await self._collect_from_web(source)
    else:
        raise ValueError(f"지원하지 않는 소스 타입: {source.type}")

async def _collect_from_web(self, source: Source) -> list[str]:
    """웹 스크래핑으로 콘텐츠 수집."""
    config = WebScraperConfig(**source.config) if source.config else None
    contents = await fetch_web(
        source_id=source.id,
        source_url=str(source.url),
        content_repo=self.content_repo,
        config=config,
    )
    return [c.id for c in contents]
```

### 의존성 추가

```toml
# pyproject.toml
dependencies = [
    # 기존 의존성...
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
]
```

---

## 3. YouTube STT 폴백 (yt-dlp + faster-whisper)

### 신규 파일
- `src/agent/domains/collector/tools/youtube_stt.py`
- `tests/unit/agent/domains/collector/test_youtube_stt.py`

### 수정 파일
- `src/agent/domains/collector/tools/youtube_tool.py` (폴백 통합)

### 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  fetch_youtube(video_id, source_id)                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. youtube-transcript-api로 기존 자막 시도                  │
│     └── 성공 → Content 생성 (PENDING 상태)                  │
└─────────────────────────────────────────────────────────────┘
                              │ TranscriptsDisabled
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. STT 폴백 (settings.STT_ENABLED=True인 경우)             │
│     ├── 영상 길이 체크 (30분 이하만)                         │
│     ├── yt-dlp로 오디오 추출 (mp3)                          │
│     ├── faster-whisper로 전사                               │
│     └── 성공 → Content 생성 (PENDING 상태)                  │
└─────────────────────────────────────────────────────────────┘
                              │ 실패
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. STT 실패 → Content 생성 (SKIPPED 상태)                  │
└─────────────────────────────────────────────────────────────┘
```

### 핵심 구현

```python
# src/agent/domains/collector/tools/youtube_stt.py

import subprocess
import tempfile
from pathlib import Path
from faster_whisper import WhisperModel
import structlog

logger = structlog.get_logger()

async def extract_audio(video_id: str, output_dir: Path) -> Path | None:
    """yt-dlp로 YouTube 오디오 추출.

    Args:
        video_id: YouTube 영상 ID
        output_dir: 출력 디렉토리

    Returns:
        추출된 오디오 파일 경로 (실패 시 None)
    """
    output_path = output_dir / f"{video_id}.mp3"

    cmd = [
        "yt-dlp",
        "-x",                          # 오디오만 추출
        "--audio-format", "mp3",
        "--audio-quality", "192K",
        "-o", str(output_path),
        f"https://www.youtube.com/watch?v={video_id}",
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        return output_path if output_path.exists() else None
    except subprocess.SubprocessError as e:
        logger.warning("오디오 추출 실패", video_id=video_id, error=str(e))
        return None


async def transcribe_audio(
    audio_path: Path,
    model_size: str = "base"
) -> str | None:
    """faster-whisper로 오디오 전사.

    Args:
        audio_path: 오디오 파일 경로
        model_size: Whisper 모델 크기 (tiny, base, small, medium, large)

    Returns:
        전사된 텍스트 (실패 시 None)
    """
    try:
        model = WhisperModel(model_size, compute_type="int8")
        segments, info = model.transcribe(str(audio_path))
        text = " ".join(segment.text for segment in segments)
        logger.info(
            "전사 완료",
            audio_path=str(audio_path),
            language=info.language,
            duration=info.duration,
        )
        return text.strip()
    except Exception as e:
        logger.warning("전사 실패", audio_path=str(audio_path), error=str(e))
        return None


async def fetch_youtube_with_stt_fallback(
    video_id: str,
    source_id: str,
    content_repo: ContentRepository,
    settings: Settings,
) -> Content | None:
    """YouTube 영상 자막 수집 (STT 폴백 포함).

    Args:
        video_id: YouTube 영상 ID
        source_id: 소스 ID
        content_repo: 콘텐츠 저장소
        settings: 앱 설정

    Returns:
        수집된 Content (실패 시 None)
    """
    # 1. 기존 자막 시도
    transcript = await get_transcript(video_id)
    if transcript:
        return await _create_content(video_id, source_id, transcript.text, content_repo)

    # 2. STT 폴백
    if not settings.STT_ENABLED:
        logger.info("STT 비활성화됨, 건너뜀", video_id=video_id)
        return None

    # 영상 길이 체크
    duration = await get_video_duration(video_id)
    if duration and duration > settings.STT_MAX_VIDEO_DURATION_MINUTES * 60:
        logger.info(
            "영상 길이 초과, STT 건너뜀",
            video_id=video_id,
            duration_minutes=duration / 60,
        )
        return None

    # 오디오 추출 + 전사
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = await extract_audio(video_id, Path(tmpdir))
        if not audio_path:
            return None

        text = await transcribe_audio(audio_path, settings.WHISPER_MODEL_SIZE)
        if not text:
            return None

        return await _create_content(video_id, source_id, text, content_repo)
```

### 설정 추가

```python
# src/config/settings.py

class Settings(BaseSettings):
    # 기존 설정...

    # YouTube STT 설정
    STT_ENABLED: bool = True
    WHISPER_MODEL_SIZE: str = "base"  # tiny, base, small, medium, large
    STT_MAX_VIDEO_DURATION_MINUTES: int = 30
```

### 의존성 추가

```toml
# pyproject.toml
dependencies = [
    # 기존 의존성...
    "yt-dlp>=2024.1.1",
    "faster-whisper>=1.0.0",
]
```

### 시스템 의존성

```dockerfile
# Dockerfile에 추가
RUN apt-get update && apt-get install -y ffmpeg
```

---

## 4. 품질 필터링 확장

### 수정 파일
- `src/services/quality_filter.py`
- `tests/unit/services/test_quality_filter.py`

### 신규 메서드

```python
# src/services/quality_filter.py

class QualityFilter:
    """콘텐츠 품질 필터링 서비스."""

    # === 기존 메서드 유지 ===
    # filter_by_relevance()
    # filter_by_status()
    # filter_by_category()
    # filter_by_categories()
    # sort_by_relevance()
    # apply_filters()
    # get_top_contents()

    # === 신규: 중복 체크 ===
    def filter_duplicates(
        self,
        contents: list[Content],
        similarity_threshold: float = 0.85,
    ) -> list[Content]:
        """유사 콘텐츠 중복 제거.

        제목 기반 Jaccard 유사도로 중복 판단.
        최신 콘텐츠 우선 유지.

        Args:
            contents: 필터링할 콘텐츠 목록
            similarity_threshold: 유사도 임계값 (0.0~1.0)

        Returns:
            중복 제거된 콘텐츠 목록
        """
        if not contents:
            return []

        # 최신순 정렬 (최신 콘텐츠 우선 유지)
        sorted_contents = sorted(
            contents,
            key=lambda c: c.collected_at or datetime.min,
            reverse=True,
        )

        unique: list[Content] = []
        for content in sorted_contents:
            is_duplicate = False
            for existing in unique:
                similarity = self._calculate_similarity(
                    content.original_title or "",
                    existing.original_title or "",
                )
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique.append(content)

        return unique

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Jaccard 유사도 계산."""
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union)

    # === 신규: 최신성 체크 ===
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
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        return [
            c for c in contents
            if c.collected_at and c.collected_at >= cutoff
        ]

    # === 신규: 품질 체크 ===
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
            품질 기준을 통과한 콘텐츠 목록
        """
        result = []
        for content in contents:
            # 제목 체크
            if require_title and not content.original_title:
                continue

            # 본문 길이 체크
            body = content.original_body or ""
            if len(body) < min_body_length:
                continue

            result.append(content)

        return result

    # === 확장된 통합 필터 ===
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
        result = contents

        # 상태 필터
        if status:
            result = self.filter_by_status(result, status)

        # 카테고리 필터
        if categories:
            result = self.filter_by_categories(result, categories)

        # 관련성 필터
        if min_relevance is not None:
            result = self.filter_by_relevance(result, min_relevance)

        # 최신성 필터
        if max_age_days is not None:
            result = self.filter_by_recency(result, max_age_days)

        # 품질 필터
        result = self.filter_by_quality(result, min_body_length, require_title)

        # 중복 제거
        if remove_duplicates:
            result = self.filter_duplicates(result, similarity_threshold)

        # 정렬
        if sort_by == "relevance":
            result = self.sort_by_relevance(result, descending=True)
        elif sort_by == "recency":
            result = sorted(
                result,
                key=lambda c: c.collected_at or datetime.min,
                reverse=True,
            )

        # 개수 제한
        if limit:
            result = result[:limit]

        return result
```

---

## 수정 파일 목록

### 모델
- [ ] `src/models/source.py` - WEB 타입 추가

### Collector 도구
- [ ] `src/agent/domains/collector/tools/web_scraper_tool.py` (신규)
- [ ] `src/agent/domains/collector/tools/youtube_stt.py` (신규)
- [ ] `src/agent/domains/collector/tools/youtube_tool.py` - STT 폴백 통합
- [ ] `src/agent/domains/collector/tools/__init__.py` - exports 추가

### 서비스
- [ ] `src/services/content_pipeline.py` - WEB 분기 추가
- [ ] `src/services/quality_filter.py` - 필터 확장

### 설정
- [ ] `src/config/settings.py` - STT 설정 추가
- [ ] `pyproject.toml` - 의존성 추가

### 테스트
- [ ] `tests/unit/models/test_source.py` - WEB 타입 테스트
- [ ] `tests/unit/agent/domains/collector/test_web_scraper_tool.py` (신규)
- [ ] `tests/unit/agent/domains/collector/test_youtube_stt.py` (신규)
- [ ] `tests/unit/agent/domains/collector/test_youtube_tool.py` - STT 폴백 테스트
- [ ] `tests/unit/services/test_quality_filter.py` - 확장 테스트
- [ ] `tests/integration/test_web_scraping_flow.py` (신규)

---

## 의존성 변경 요약

```toml
# pyproject.toml에 추가
dependencies = [
    # 웹 스크래핑
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",

    # YouTube STT
    "yt-dlp>=2024.1.1",
    "faster-whisper>=1.0.0",
]
```

---

## 리스크 및 대응

| 리스크 | 영향도 | 대응 방안 |
|-------|-------|---------|
| faster-whisper 메모리 부족 | 높음 | base 모델 사용, Cloud Run 2GB+ 설정 |
| yt-dlp 차단 | 중간 | 버전 자동 업데이트, 요청 간격 조절 |
| 웹 스크래핑 차단 | 중간 | User-Agent 로테이션, 요청 간격 조절 |
| Playwright 속도 | 중간 | 브라우저 재사용, 필요시 병렬 처리 |

---

## 테스트 전략

### 유닛 테스트

| 모듈 | 테스트 케이스 |
|-----|-------------|
| web_scraper_tool | 각 단계별 성공/실패, 폴백 체인, 중복 건너뛰기 |
| youtube_stt | 오디오 추출, Whisper 전사, 기존 자막 있을 때 건너뛰기 |
| quality_filter | 중복 제거, 최신성 필터, 품질 체크, 통합 필터 |

### 통합 테스트

| 시나리오 | 검증 항목 |
|---------|---------|
| 웹 스크래핑 플로우 | Source → fetch_web → Content 저장 |
| STT 폴백 플로우 | 자막 없는 영상 → STT → Content 저장 |
| 다이제스트 품질 | 수집 → 필터링 → 다이제스트 발송 |

---

## 참고 자료

- [Playwright Python](https://playwright.dev/python/)
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
