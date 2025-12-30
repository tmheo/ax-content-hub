# Research: Phase 2 콘텐츠 수집 확장

**Date**: 2025-12-30
**Feature Branch**: `003-phase2-collection-expansion`

## Executive Summary

Phase 2 구현을 위한 기술 리서치 결과입니다. 웹 스크래핑, YouTube STT, 중복 감지에 대한 최적의 접근 방식을 정의합니다.

---

## 1. 웹 스크래핑 (4단계 폴백 전략)

### Decision: Playwright + BeautifulSoup 조합

**Rationale**:
- Playwright는 이미 프로젝트 의존성에 포함됨
- 4단계 폴백으로 80%+ 웹사이트 지원 가능
- Cloud Run 2GB 메모리에서 안정적 동작

**Alternatives Considered**:
| 옵션 | 장점 | 단점 | 결정 |
|------|------|------|------|
| Selenium | 레거시 지원 | 무겁고 느림 | ❌ |
| Puppeteer | Node.js 생태계 | Python 프로젝트 | ❌ |
| **Playwright** | 빠름, 안정적 | 브라우저 크기 | ✅ |
| httpx only | 가볍고 빠름 | JS 렌더링 불가 | Stage 1만 사용 |

### 4단계 폴백 구현 전략

```
Stage 1: Static HTML (httpx + BeautifulSoup)
  ↓ 실패 시
Stage 2: Dynamic JS (Playwright + CSS selector)
  ↓ 실패 시
Stage 3: Structural (DOM 휴리스틱)
  ↓ 실패 시
Stage 4: URL Pattern (링크 분석)
```

### 주요 설정값

| 설정 | 값 | 근거 |
|------|-----|------|
| 총 타임아웃 | 60초 | SC-006 요구사항 |
| Stage 1 타임아웃 | 10초 | 정적 요청 기준 |
| Stage 2 타임아웃 | 30초 | JS 렌더링 대기 |
| 최소 콘텐츠 길이 | 200자 | 유의미한 본문 기준 |
| 요청 간격 | 2-5초 | Rate limiting 대응 |

### Cloud Run 최적화

```python
BROWSER_ARGS = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',  # /dev/shm 제한 우회
    '--disable-gpu',
    '--single-process',
    '--js-flags=--max-old-space-size=512',
]
```

### 의존성 추가

```toml
# pyproject.toml
dependencies = [
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
]
```

---

## 2. YouTube STT 폴백 (faster-whisper)

### Decision: faster-whisper small 모델 + int8 양자화

**Rationale**:
- 2GB 메모리 제약에서 small 모델이 최적
- int8 양자화로 CPU에서 효율적 추론
- VAD 필터로 2-4배 속도 향상

**Alternatives Considered**:
| 옵션 | 장점 | 단점 | 결정 |
|------|------|------|------|
| Google STT API | 정확, 관리 불필요 | 비용 높음 | ❌ |
| OpenAI Whisper API | 정확 | 속도 느림, 비용 | ❌ |
| **faster-whisper** | 빠름, 무료 | 로컬 리소스 필요 | ✅ |
| whisper.cpp | 경량 | 파이썬 통합 어려움 | ❌ |

### 모델 선택 기준

| 모델 | 메모리 | 30분 영상 처리 | 한국어 정확도 |
|------|--------|----------------|---------------|
| tiny | ~1GB | 5-10분 | 낮음 |
| base | ~1GB | 8-15분 | 보통 |
| **small** | ~2GB | 15-30분 | 양호 |
| medium | ~5GB | 30-60분 | 좋음 |

### 주요 설정값

| 설정 | 값 | 근거 |
|------|-----|------|
| 모델 크기 | small | 2GB 메모리 제약 |
| compute_type | int8 | CPU 최적화 |
| 최대 영상 길이 | 30분 | SC-007 (10분 내 처리) |
| VAD 활성화 | True | 무음 스킵 |
| 기본 언어 | auto | 자동 감지 후 명시 |

### 오디오 추출 (yt-dlp)

```python
ydl_opts = {
    "format": "bestaudio/best",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "m4a",  # YouTube 네이티브
        "preferredquality": "192",
    }],
}
```

### 의존성 추가

```toml
# pyproject.toml
dependencies = [
    "yt-dlp>=2024.1.1",
    "faster-whisper>=1.0.0",
]
```

### 시스템 의존성

```dockerfile
# Dockerfile
RUN apt-get update && apt-get install -y ffmpeg
```

---

## 3. 중복 콘텐츠 감지

### Decision: Jaccard Similarity 기반 토큰 비교

**Rationale**:
- 구현 간단, 계산 비용 낮음
- 제목 기반 비교에 충분한 정확도
- 임베딩 대비 의존성/리소스 최소화

**Alternatives Considered**:
| 옵션 | 장점 | 단점 | 결정 |
|------|------|------|------|
| **Jaccard** | 간단, 빠름 | 의미 유사성 미반영 | ✅ MVP |
| TF-IDF + Cosine | 가중치 반영 | 어휘 사전 필요 | 고려 가능 |
| Levenshtein | 오타 감지 | 순서 민감 | ❌ |
| Semantic Embedding | 의미 파악 | GPU/모델 필요 | Phase 3 고려 |

### 토큰화 전략

**한국어 최적화**: 형태소 분석 없이 공백 분리 + 영어 토큰
- KoNLPy 의존성 없이 구현 가능
- 제목 길이가 짧아 단순 토큰화로 충분

```python
def tokenize_for_similarity(text: str) -> set[str]:
    """유사도 비교용 토큰화 (한영 혼합)"""
    # 소문자 + 공백 분리
    tokens = set(text.lower().split())
    # 1자 토큰 제외 (조사 등)
    return {t for t in tokens if len(t) > 1}
```

### 주요 설정값

| 설정 | 값 | 근거 |
|------|-----|------|
| 유사도 임계값 | 0.85 | FR-017 기본값 |
| 비교 기준 | 제목 | FR-016 |
| 우선순위 | 최신 우선 | FR-018 |

### 성능 고려사항

- 일일 콘텐츠 < 100개 → O(n²) 허용
- 7일 윈도우 내 비교로 범위 제한
- 필요시 MinHash LSH로 확장 가능

---

## 4. 품질 필터링 확장

### Decision: 기존 QualityFilter 클래스 확장

**Rationale**:
- 기존 필터 패턴 재사용
- 새 필터 메서드 추가로 확장
- 통합 메서드로 조합 적용

### 신규 필터 메서드

| 메서드 | 파라미터 | 기본값 |
|--------|----------|--------|
| `filter_duplicates` | similarity_threshold | 0.85 |
| `filter_by_recency` | max_age_days | 7 |
| `filter_by_quality` | min_body_length, require_title | 100, True |
| `apply_all_filters` | (통합 메서드) | - |

---

## 5. 설정 추가

### Settings 클래스 확장

```python
# src/config/settings.py

# 웹 스크래핑 설정
SCRAPING_TIMEOUT_SECONDS: int = 60
SCRAPING_MIN_CONTENT_LENGTH: int = 200
SCRAPING_REQUEST_INTERVAL_MIN: float = 2.0
SCRAPING_REQUEST_INTERVAL_MAX: float = 5.0

# YouTube STT 설정
STT_ENABLED: bool = True
STT_MODEL_SIZE: str = "small"  # tiny, base, small, medium
STT_COMPUTE_TYPE: str = "int8"
STT_MAX_VIDEO_DURATION_MINUTES: int = 30

# 품질 필터링 설정
QUALITY_SIMILARITY_THRESHOLD: float = 0.85
QUALITY_MAX_AGE_DAYS: int = 7
QUALITY_MIN_BODY_LENGTH: int = 100
QUALITY_REQUIRE_TITLE: bool = True
```

---

## 6. 리스크 및 완화 방안

| 리스크 | 영향도 | 완화 방안 |
|--------|--------|-----------|
| faster-whisper OOM | 높음 | 영상 길이 제한 (30분), small 모델 |
| yt-dlp 차단 | 중간 | User-Agent 로테이션, 재시도 로직 |
| 웹 스크래핑 차단 | 중간 | 요청 간격 조절, Stealth 스크립트 |
| 한국어 STT 정확도 | 중간 | language="ko" 명시, 후처리 검토 |

---

## 7. 참고 자료

### 웹 스크래핑
- [Playwright Python Docs](https://playwright.dev/python/)
- [BeautifulSoup Docs](https://www.crummy.com/software/BeautifulSoup/)

### YouTube STT
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)
- [Cloud Run GPU](https://docs.cloud.google.com/run/docs/configuring/services/gpu)

### 중복 감지
- [MinHash LSH (datasketch)](https://github.com/ekzhu/datasketch)
- [Sentence Transformers](https://www.sbert.net/)
