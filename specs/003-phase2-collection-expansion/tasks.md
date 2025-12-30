# Tasks: Phase 2 콘텐츠 수집 확장

**Input**: Design documents from `/specs/003-phase2-collection-expansion/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/tool-interfaces.md ✅

**TDD Workflow**: 헌법 원칙 I "Test-First (NON-NEGOTIABLE)"에 따라 모든 주요 기능은 테스트를 먼저 작성한 후 구현합니다.
- 각 User Story 내에서 테스트 태스크(Txx-TEST)가 구현 태스크보다 먼저 위치
- Red → Green → Refactor 사이클 준수

**Organization**: 태스크는 User Story별로 그룹화되어 독립적으로 구현 및 테스트 가능.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (다른 파일, 의존성 없음)
- **[Story]**: 해당 태스크가 속한 User Story (예: US1, US2, US3)
- 설명에 정확한 파일 경로 포함

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 프로젝트 의존성 추가 및 기본 구조 준비

- [x] T001 [P] pyproject.toml에 beautifulsoup4, lxml 의존성 추가
- [x] T002 [P] pyproject.toml에 yt-dlp 의존성 추가
- [x] T003 [P] pyproject.toml에 faster-whisper 의존성 추가
- [x] T004 Dockerfile에 ffmpeg 시스템 패키지 추가 (STT용)
- [x] T005 uv sync로 의존성 설치 및 검증

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 User Story에서 공통으로 사용하는 인프라 설정

**⚠️ CRITICAL**: 이 Phase 완료 전에 User Story 작업 불가

- [x] T006 [P] src/config/settings.py에 웹 스크래핑 설정 추가 (SCRAPING_TIMEOUT_SECONDS, SCRAPING_MIN_CONTENT_LENGTH, SCRAPING_REQUEST_INTERVAL_MIN/MAX)
- [x] T007 [P] src/config/settings.py에 YouTube STT 설정 추가 (STT_ENABLED, STT_MODEL_SIZE, STT_COMPUTE_TYPE, STT_MAX_VIDEO_DURATION_MINUTES)
- [x] T008 [P] src/config/settings.py에 품질 필터링 설정 추가 (QUALITY_SIMILARITY_THRESHOLD, QUALITY_MAX_AGE_DAYS, QUALITY_MIN_BODY_LENGTH, QUALITY_REQUIRE_TITLE)
- [x] T009 src/models/source.py의 SourceType Enum에 WEB = "web" 추가

**Checkpoint**: Foundation 완료 - User Story 구현 시작 가능

---

## Phase 3: User Story 1 - RSS 없는 웹사이트 콘텐츠 수집 (Priority: P1) 🎯 MVP

**Goal**: WEB 타입 소스에서 4단계 폴백 전략으로 콘텐츠를 자동 추출

**Independent Test**: WEB 타입 소스를 등록하고 수집을 실행하면 해당 웹사이트에서 콘텐츠가 추출되어 저장되는 것을 확인

### Tests for US1 (TDD: Write First)

- [x] T010 [P] [US1] tests/unit/agent/domains/collector/tools/test_web_scraper_tool.py 파일 생성 및 테스트 fixture 설정
- [x] T011 [P] [US1] test_web_scraper_tool.py에 WebScraperConfig, ScrapedContent dataclass 테스트 작성
- [x] T012 [US1] test_web_scraper_tool.py에 Stage 1 (Static HTML) 추출 테스트 작성 (mock httpx response)
- [x] T013 [US1] test_web_scraper_tool.py에 Stage 2 (Dynamic JS) 추출 테스트 작성 (mock Playwright)
- [x] T014 [US1] test_web_scraper_tool.py에 Stage 3 (Structural) 추출 테스트 작성
- [x] T015 [US1] test_web_scraper_tool.py에 Stage 4 (URL Pattern) 추출 테스트 작성
- [x] T016 [US1] test_web_scraper_tool.py에 fetch_web() 4단계 폴백 오케스트레이션 테스트 작성
- [x] T017 [US1] test_web_scraper_tool.py에 예외 처리 테스트 작성 (ScrapingError, TimeoutError, NetworkError)

### Value Objects for US1

- [x] T018 [P] [US1] src/agent/domains/collector/tools/web_scraper_tool.py에 WebScraperConfig dataclass 생성 (selector, wait_for, url_pattern, timeout_seconds 필드)
- [x] T019 [P] [US1] src/agent/domains/collector/tools/web_scraper_tool.py에 ScrapedContent dataclass 생성 (url, title, body, published_at, extraction_stage 필드)

### Web Scraper Implementation for US1

- [x] T020 [US1] src/agent/domains/collector/tools/web_scraper_tool.py에 Stage 1: Static HTML 추출 구현 (httpx + BeautifulSoup)
- [x] T021 [US1] src/agent/domains/collector/tools/web_scraper_tool.py에 Stage 2: Dynamic JS 추출 구현 (Playwright + CSS selector)
- [x] T022 [US1] src/agent/domains/collector/tools/web_scraper_tool.py에 Stage 3: Structural 추출 구현 (DOM 휴리스틱)
- [x] T023 [US1] src/agent/domains/collector/tools/web_scraper_tool.py에 Stage 4: URL Pattern 추출 구현 (링크 분석)
- [x] T024 [US1] src/agent/domains/collector/tools/web_scraper_tool.py에 fetch_web() 함수 구현 (4단계 폴백 오케스트레이션)
- [x] T025 [US1] src/agent/domains/collector/tools/web_scraper_tool.py에 ScrapingError, TimeoutError, NetworkError 예외 클래스 추가

### Pipeline Integration for US1

- [x] T026 [US1] tests/unit/services/test_content_pipeline.py에 _collect_from_web() 테스트 추가
- [x] T027 [US1] src/services/content_pipeline.py에 _collect_from_web() 메서드 추가
- [x] T028 [US1] src/services/content_pipeline.py의 _collect_from_source()에 SourceType.WEB 라우팅 추가

**Checkpoint**: User Story 1 완료 - WEB 소스 수집 독립적으로 테스트 가능

---

## Phase 4: User Story 2 - 자막 없는 YouTube 영상 수집 (Priority: P1)

**Goal**: 기존 자막이 없는 YouTube 영상에서 음성 인식(STT)을 통해 텍스트 추출

**Independent Test**: 자막이 없는 YouTube 영상 URL을 포함한 소스에서 수집을 실행하면 음성 인식된 텍스트가 저장되는 것을 확인

### Tests for US2 (TDD: Write First)

- [x] T029 [P] [US2] tests/unit/agent/domains/collector/tools/test_youtube_stt.py 파일 생성 및 테스트 fixture 설정
- [x] T030 [P] [US2] test_youtube_stt.py에 TranscriptionResult dataclass 테스트 작성
- [x] T031 [US2] test_youtube_stt.py에 예외 클래스 테스트 작성 (YouTubeExtractionError, AgeRestrictedError 등)
- [x] T032 [US2] test_youtube_stt.py에 extract_audio() 테스트 작성 (mock yt-dlp)
- [x] T033 [US2] test_youtube_stt.py에 transcribe_audio() 테스트 작성 (mock faster-whisper)
- [x] T034 [US2] test_youtube_stt.py에 영상 길이 제한 테스트 작성
- [x] T035 [US2] test_youtube_stt.py에 임시 파일 자동 삭제 테스트 작성

### Value Objects for US2

- [x] T036 [P] [US2] src/agent/domains/collector/tools/youtube_stt.py에 TranscriptionResult dataclass 생성 (text, language, language_probability, duration_seconds 필드)
- [x] T037 [P] [US2] src/agent/domains/collector/tools/youtube_stt.py에 YouTubeExtractionError, AgeRestrictedError, VideoUnavailableError, TranscriptionError 예외 클래스 추가

### YouTube STT Implementation for US2

- [x] T038 [US2] src/agent/domains/collector/tools/youtube_stt.py에 extract_audio() 함수 구현 (yt-dlp로 오디오 추출)
- [x] T039 [US2] src/agent/domains/collector/tools/youtube_stt.py에 transcribe_audio() 함수 구현 (faster-whisper로 전사)
- [x] T040 [US2] src/agent/domains/collector/tools/youtube_stt.py에 영상 길이 확인 로직 추가 (STT_MAX_VIDEO_DURATION_MINUTES 기준)
- [x] T041 [US2] src/agent/domains/collector/tools/youtube_stt.py에 임시 오디오 파일 자동 삭제 로직 추가

### YouTube Tool Integration for US2

- [x] T042 [US2] tests/unit/agent/domains/collector/tools/test_youtube_tool.py에 fetch_youtube_with_stt() 테스트 추가
- [x] T043 [US2] src/agent/domains/collector/tools/youtube_tool.py에 fetch_youtube_with_stt() 함수 추가 (STT 폴백 포함)
- [x] T044 [US2] src/agent/domains/collector/tools/youtube_tool.py의 기존 fetch_youtube()에서 자막 없을 때 STT 폴백 호출 통합

**Checkpoint**: User Story 2 완료 - YouTube STT 수집 독립적으로 테스트 가능

---

## Phase 5: User Story 3 - 중복 콘텐츠 필터링 (Priority: P2)

**Goal**: 제목 유사도 기반으로 중복 콘텐츠를 식별하고 최신 콘텐츠만 유지

**Independent Test**: 유사한 제목의 콘텐츠 여러 개를 수집한 후 필터링을 적용하면 중복이 제거되는 것을 확인

### Tests for US3 (TDD: Write First)

- [x] T045 [P] [US3] tests/unit/services/test_quality_filter.py에 중복 필터링 테스트 섹션 추가
- [x] T046 [P] [US3] test_quality_filter.py에 _tokenize() 테스트 작성
- [x] T047 [P] [US3] test_quality_filter.py에 _calculate_similarity() Jaccard 유사도 테스트 작성
- [x] T048 [US3] test_quality_filter.py에 filter_duplicates() 테스트 작성 (유사도 임계값, 최신 우선 검증)

### Implementation for US3

- [x] T049 [P] [US3] src/services/quality_filter.py에 _tokenize() private 메서드 추가 (유사도 비교용 토큰화)
- [x] T050 [P] [US3] src/services/quality_filter.py에 _calculate_similarity() private 메서드 추가 (Jaccard 유사도 계산)
- [x] T051 [US3] src/services/quality_filter.py에 filter_duplicates() 메서드 추가 (제목 유사도 기반 중복 제거, 최신 우선)

**Checkpoint**: User Story 3 완료 - 중복 필터링 독립적으로 테스트 가능

---

## Phase 6: User Story 4 - 최신성 기반 필터링 (Priority: P2)

**Goal**: 수집일 기준 N일 이내 콘텐츠만 필터링하여 시의적절한 정보 제공

**Independent Test**: 다양한 날짜의 콘텐츠를 수집한 후 최신성 필터를 적용하면 기준일 이내의 콘텐츠만 남는 것을 확인

### Tests for US4 (TDD: Write First)

- [x] T052 [US4] tests/unit/services/test_quality_filter.py에 filter_by_recency() 테스트 작성 (max_age_days, 수집일 없는 콘텐츠 처리 검증)

### Implementation for US4

- [x] T053 [US4] src/services/quality_filter.py에 filter_by_recency() 메서드 추가 (max_age_days 기준 필터링)

**Checkpoint**: User Story 4 완료 - 최신성 필터링 독립적으로 테스트 가능

---

## Phase 7: User Story 5 - 콘텐츠 품질 검증 (Priority: P2)

**Goal**: 본문 길이와 제목 유무 기준으로 저품질 콘텐츠 제외

**Independent Test**: 본문 길이가 다양한 콘텐츠를 수집한 후 품질 필터를 적용하면 기준 미달 콘텐츠가 제외되는 것을 확인

### Tests for US5 (TDD: Write First)

- [x] T054 [US5] tests/unit/services/test_quality_filter.py에 filter_by_quality() 테스트 작성 (min_body_length, require_title 검증)
- [x] T055 [US5] test_quality_filter.py에 apply_all_filters() 통합 테스트 작성 (모든 필터 조합 검증)

### Implementation for US5

- [x] T056 [US5] src/services/quality_filter.py에 filter_by_quality() 메서드 추가 (min_body_length, require_title 기준)
- [x] T057 [US5] src/services/quality_filter.py에 apply_all_filters() 통합 메서드 추가 (모든 필터 조합 적용)

**Checkpoint**: User Story 5 완료 - 품질 필터링 독립적으로 테스트 가능

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 여러 User Story에 걸친 개선 및 마무리

- [x] T058 [P] .env.example에 Phase 2 환경 변수 추가 (SCRAPING_*, STT_*, QUALITY_*)
- [x] T059 [P] Cloud Run 최적화 브라우저 인자 상수 추가 (BROWSER_ARGS: --no-sandbox, --disable-dev-shm-usage, --disable-gpu)
- [x] T060 tests/integration/test_web_scraping_flow.py 통합 테스트 작성 (WEB 소스 E2E)
- [x] T061 tests/integration/test_youtube_stt_flow.py 통합 테스트 작성 (STT 폴백 E2E)
- [x] T062 quickstart.md 기반 전체 플로우 검증 실행
- [x] T063 ruff check, ruff format, mypy 실행 및 수정

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 의존성 없음 - 즉시 시작 가능
- **Foundational (Phase 2)**: Setup 완료 필요 - 모든 User Story를 BLOCKS
- **User Stories (Phase 3-7)**: Foundational 완료 필요
  - US1, US2는 P1으로 우선 순위 동일하나 독립적
  - US3, US4, US5는 P2로 모두 QualityFilter 관련이지만 독립적으로 구현 가능
- **Polish (Phase 8)**: 모든 User Story 완료 후

### User Story Dependencies

| Story | 우선순위 | 의존 Story | 병렬 가능 |
|-------|---------|-----------|----------|
| US1 (웹 스크래핑) | P1 | None | ✅ |
| US2 (YouTube STT) | P1 | None | ✅ (US1과 병렬) |
| US3 (중복 필터) | P2 | None | ✅ |
| US4 (최신성 필터) | P2 | None | ✅ (US3과 병렬) |
| US5 (품질 필터) | P2 | None | ✅ (US3, US4와 병렬) |

### Within Each User Story (TDD Cycle)

1. **테스트 작성 (Red)**: 테스트 파일 생성 → 테스트 케이스 작성 → 실패 확인
2. **구현 (Green)**: Value Objects → 핵심 로직 → 테스트 통과 확인
3. **리팩토링**: 코드 정리, 파이프라인/통합

### Parallel Opportunities

- **Phase 1**: T001, T002, T003 병렬 실행 가능
- **Phase 2**: T006, T007, T008 병렬 실행 가능
- **Phase 3**: T010, T011 (테스트 fixture) 병렬 → T018, T019 (구현) 병렬
- **Phase 4**: T029, T030 (테스트 fixture) 병렬 → T036, T037 (구현) 병렬
- **Phase 5**: T045, T046, T047 (테스트) 병렬 → T049, T050 (구현) 병렬
- **Phase 8**: T058, T059 병렬 실행 가능

---

## Parallel Example: Phase 3 (User Story 1) - TDD Workflow

```bash
# 1. 테스트 파일 생성 (병렬):
T010: "tests/unit/.../test_web_scraper_tool.py 파일 생성"
T011: "dataclass 테스트 작성"

# 2. 테스트 작성 (순차 - Red):
T012-T017: "각 Stage 및 fetch_web() 테스트 작성"

# 3. 구현 (Green - 테스트 통과):
T018-T019: "Value Objects 구현 (병렬)"
T020-T025: "Stage 1-4 + fetch_web() + 예외 클래스 구현 (순차)"

# 4. 통합:
T026: "파이프라인 테스트 작성"
T027-T028: "파이프라인 통합 구현"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 완료: Setup
2. Phase 2 완료: Foundational (CRITICAL - 모든 Story 차단)
3. Phase 3 완료: User Story 1 (웹 스크래핑)
4. **STOP and VALIDATE**: WEB 소스 수집 독립 테스트
5. 필요시 배포/데모

### Incremental Delivery

1. Setup + Foundational → 기반 완료
2. User Story 1 (P1) → 웹 스크래핑 가능 (MVP!)
3. User Story 2 (P1) → YouTube STT 가능
4. User Story 3-5 (P2) → 품질 필터링 완성
5. Polish → 최종 검증

### Parallel Team Strategy

여러 개발자 협업 시:

1. 팀 전체가 Setup + Foundational 완료
2. Foundational 완료 후:
   - 개발자 A: User Story 1 (웹 스크래핑)
   - 개발자 B: User Story 2 (YouTube STT)
3. P1 완료 후:
   - 개발자 A: User Story 3 (중복 필터)
   - 개발자 B: User Story 4 + 5 (최신성/품질 필터)

---

## Summary

| 항목 | 수치 |
|------|------|
| 총 태스크 수 | **63개** |
| Phase 1 (Setup) | 5개 |
| Phase 2 (Foundational) | 4개 |
| Phase 3 (US1 - 웹 스크래핑) | **19개** (테스트 8 + 구현 11) |
| Phase 4 (US2 - YouTube STT) | **16개** (테스트 8 + 구현 8) |
| Phase 5 (US3 - 중복 필터) | **7개** (테스트 4 + 구현 3) |
| Phase 6 (US4 - 최신성 필터) | **2개** (테스트 1 + 구현 1) |
| Phase 7 (US5 - 품질 필터) | **4개** (테스트 2 + 구현 2) |
| Phase 8 (Polish) | **6개** (통합 테스트 2 포함) |
| 테스트 태스크 | **25개** (40%) |
| 병렬 가능 태스크 | 22개 (35%) |

### MVP Scope (권장)

**Phase 1 + Phase 2 + Phase 3 = 28개 태스크**

웹 스크래핑 기능만으로도 "RSS 없는 사이트 수집" 가치 제공

### TDD Coverage

| User Story | 테스트 태스크 | 구현 태스크 | TDD 비율 |
|------------|--------------|------------|---------|
| US1 (웹 스크래핑) | 9개 | 10개 | 47% |
| US2 (YouTube STT) | 8개 | 8개 | 50% |
| US3 (중복 필터) | 4개 | 3개 | 57% |
| US4 (최신성 필터) | 1개 | 1개 | 50% |
| US5 (품질 필터) | 2개 | 2개 | 50% |

---

## Notes

- **TDD 필수**: 헌법 원칙 I에 따라 테스트를 먼저 작성 (Red → Green → Refactor)
- [P] 태스크 = 다른 파일, 의존성 없음
- [Story] 레이블 = 해당 User Story에 대한 추적성
- 각 User Story는 독립적으로 완료 및 테스트 가능
- 각 태스크 또는 논리적 그룹 후 커밋 권장
- 어느 Checkpoint에서든 멈추고 Story 독립 검증 가능
- **테스트 태스크 → 구현 태스크** 순서 준수 필수
