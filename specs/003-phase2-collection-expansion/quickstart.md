# Quickstart: Phase 2 콘텐츠 수집 확장

**Date**: 2025-12-30
**Feature Branch**: `003-phase2-collection-expansion`

## Prerequisites

### 시스템 요구사항

```bash
# Python 3.12+
python --version  # Python 3.12.x

# uv 패키지 매니저
uv --version

# ffmpeg (YouTube STT용)
ffmpeg -version

# Playwright 브라우저 (웹 스크래핑용)
uv run playwright install chromium
```

### 환경 변수 (.env)

```bash
# 기존 필수 설정
GCP_PROJECT_ID=your-project
GOOGLE_API_KEY=your-gemini-api-key
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...

# Firestore 에뮬레이터 (로컬 개발)
FIRESTORE_EMULATOR_HOST=localhost:8086

# Phase 2 신규 설정 (선택, 기본값 있음)
STT_ENABLED=true
STT_MODEL_SIZE=small
STT_MAX_VIDEO_DURATION_MINUTES=30
QUALITY_SIMILARITY_THRESHOLD=0.85
```

---

## Quick Setup

### 1. 의존성 설치

```bash
# Phase 2 의존성 추가 후
uv sync --all-extras

# Playwright 브라우저 설치
uv run playwright install chromium
```

### 2. 로컬 서비스 시작

```bash
# Firestore 에뮬레이터
docker compose up -d

# 개발 서버
FIRESTORE_EMULATOR_HOST=localhost:8086 uv run uvicorn src.api.main:app --reload --port 8080
```

---

## Usage Examples

### 1. WEB 타입 소스 등록

```bash
# API로 WEB 소스 등록
curl -X POST http://localhost:8080/api/sources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AI Blog (No RSS)",
    "type": "web",
    "url": "https://example.com/blog",
    "config": {
      "selector": ".blog-post",
      "wait_for": ".blog-list",
      "url_pattern": "/blog/\\d{4}/"
    },
    "category": "AI_RESEARCH",
    "language": "en"
  }'
```

### 2. 수집 테스트

```bash
# 수집 트리거 (Cloud Scheduler 시뮬레이션)
curl -X POST http://localhost:8080/scheduler/collect
```

### 3. 품질 필터링 테스트

```python
# Python REPL에서 테스트
from src.services.quality_filter import QualityFilter
from src.models.content import Content

filter = QualityFilter()

# 중복 제거 테스트
contents = [...]  # Content 목록
unique = filter.filter_duplicates(contents, similarity_threshold=0.85)

# 통합 필터 테스트
filtered = filter.apply_all_filters(
    contents,
    min_relevance=0.3,
    max_age_days=7,
    remove_duplicates=True,
    min_body_length=100,
    require_title=True,
)
```

---

## Testing

### 단위 테스트

```bash
# 전체 테스트
uv run pytest tests/ -v

# Phase 2 관련 테스트만
uv run pytest tests/unit/agent/domains/collector/ -v
uv run pytest tests/unit/services/test_quality_filter.py -v
uv run pytest tests/unit/models/test_source.py -v
```

### 통합 테스트

```bash
# Firestore 에뮬레이터 필요
FIRESTORE_EMULATOR_HOST=localhost:8086 uv run pytest tests/integration/ -v -m integration
```

---

## Code Quality

```bash
# 린팅 + 포맷팅
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/

# 타입 체크
uv run mypy src/

# pre-commit
uv run pre-commit run --all-files
```

---

## Debugging Tips

### 웹 스크래핑 디버그

```python
# 특정 URL 스크래핑 테스트
from src.agent.domains.collector.tools.web_scraper_tool import fetch_web

result = await fetch_web(
    source_id="test",
    source_url="https://example.com/blog",
    content_repo=mock_repo,
    config=WebScraperConfig(selector=".post"),
)
print(f"Stage: {result[0].extraction_stage if result else 'Failed'}")
```

### YouTube STT 디버그

```python
# STT 폴백 테스트
from src.agent.domains.collector.tools.youtube_stt import transcribe_audio

result = await transcribe_audio("/tmp/audio.m4a", model_size="small")
print(f"Language: {result.language}, Text: {result.text[:200]}...")
```

### 품질 필터 디버그

```python
# 유사도 계산 확인
filter = QualityFilter()
sim = filter._calculate_similarity(
    "OpenAI GPT-4 출시",
    "GPT-4 공개, OpenAI"
)
print(f"Similarity: {sim:.2%}")
```

---

## Common Issues

### Playwright 브라우저 없음

```bash
# 에러: Browser not installed
# 해결:
uv run playwright install chromium
```

### ffmpeg 없음

```bash
# 에러: ffmpeg not found
# 해결 (macOS):
brew install ffmpeg

# 해결 (Ubuntu):
sudo apt-get install ffmpeg
```

### STT 메모리 부족

```bash
# 에러: OOM during transcription
# 해결: 작은 모델 사용
STT_MODEL_SIZE=base  # 또는 tiny
```

### 웹 스크래핑 차단

```
# 에러: 403 Forbidden
# 해결:
# 1. 요청 간격 늘리기 (SCRAPING_REQUEST_INTERVAL_MIN/MAX)
# 2. User-Agent 확인
# 3. 해당 사이트의 robots.txt 확인
```
