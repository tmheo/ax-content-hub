# Tasks: Phase 1 MVP - 핵심 파이프라인

**Input**: Design documents from `/specs/002-phase1-mvp-pipeline/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/openapi.yaml

**Tests**: TDD 필수 (Constitution I. Test-First 원칙)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 프로젝트 초기화 및 새 의존성 추가

- [x] T001 Add Phase 1 dependencies to pyproject.toml (feedparser, youtube-transcript-api, google-genai)
- [x] T002 [P] Create src/models/__init__.py with model exports
- [x] T003 [P] Create src/repositories/__init__.py with repository exports
- [x] T004 [P] Create src/services/__init__.py with service exports
- [x] T005 [P] Create src/agent/domains/__init__.py
- [x] T006 [P] Create tests/unit/models/__init__.py
- [x] T007 [P] Create tests/unit/repositories/__init__.py
- [x] T008 [P] Create tests/unit/services/__init__.py
- [x] T009 [P] Create tests/integration/__init__.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 User Story에서 사용하는 핵심 인프라

**⚠️ CRITICAL**: 이 Phase 완료 전 User Story 작업 불가

### 2.1 Pydantic Models (data-model.md 기반)

- [x] T010 [P] Write tests for Source model in tests/unit/models/test_source.py
- [x] T011 [P] Write tests for Content model in tests/unit/models/test_content.py
- [x] T012 [P] Write tests for Subscription model in tests/unit/models/test_subscription.py
- [x] T013 [P] Write tests for Digest model in tests/unit/models/test_digest.py
- [x] T014 [P] Implement Source model in src/models/source.py
- [x] T015 [P] Implement Content model in src/models/content.py
- [x] T016 [P] Implement Subscription model in src/models/subscription.py
- [x] T017 [P] Implement Digest model in src/models/digest.py
- [x] T018 Implement URL normalization and content_key generation in src/models/content.py

### 2.2 Repository Base

- [x] T019 Write tests for BaseRepository in tests/unit/repositories/test_base.py
- [x] T020 Implement BaseRepository in src/repositories/base.py

### 2.3 Gemini Client Adapter

- [x] T021 Write tests for GeminiClient in tests/unit/adapters/test_gemini_client.py
- [x] T022 Implement GeminiClient in src/adapters/gemini_client.py
- [x] T023 Add GOOGLE_API_KEY to src/config/settings.py

### 2.4 Extend Settings

- [x] T024 Add Phase 1 configuration fields to src/config/settings.py (TASKS_MODE, etc.)

**Checkpoint**: Foundation ready - User Story 구현 시작 가능

---

## Phase 3: User Story 1 - RSS 피드 콘텐츠 수집 (Priority: P1) 🎯

**Goal**: RSS 피드에서 새 콘텐츠를 수집하고 Firestore에 저장

**Independent Test**: RSS 피드 URL 등록 후 수집 트리거 → contents 컬렉션에 저장 확인

### Tests for User Story 1

- [x] T025 [P] [US1] Write unit tests for SourceRepository in tests/unit/repositories/test_source_repo.py
- [x] T026 [P] [US1] Write unit tests for ContentRepository in tests/unit/repositories/test_content_repo.py
- [x] T027 [P] [US1] Write unit tests for rss_tool in tests/unit/agent/domains/collector/test_rss_tool.py
- [x] T028 [US1] Write integration test for RSS collection flow in tests/integration/test_collection_flow.py

### Implementation for User Story 1

- [x] T029 [P] [US1] Implement SourceRepository in src/repositories/source_repo.py
- [x] T030 [P] [US1] Implement ContentRepository in src/repositories/content_repo.py
- [x] T031 [US1] Implement fetch_rss tool in src/agent/domains/collector/tools/rss_tool.py
- [x] T032 [US1] Create src/agent/domains/collector/__init__.py
- [x] T033 [US1] Create src/agent/domains/collector/tools/__init__.py

**Checkpoint**: RSS 수집 단독 테스트 가능

---

## Phase 4: User Story 2 - YouTube 자막 수집 (Priority: P1)

**Goal**: YouTube 영상에서 기존 자막 추출하여 저장

**Independent Test**: YouTube 영상 ID 입력 → 자막 텍스트가 contents에 저장 확인

### Tests for User Story 2

- [x] T034 [P] [US2] Write unit tests for youtube_tool in tests/unit/agent/domains/collector/test_youtube_tool.py

### Implementation for User Story 2

- [x] T035 [US2] Implement fetch_youtube tool in src/agent/domains/collector/tools/youtube_tool.py

**Checkpoint**: YouTube 자막 수집 단독 테스트 가능

---

## Phase 5: User Story 3 - 콘텐츠 번역 및 요약 (Priority: P1)

**Goal**: 영문 콘텐츠를 한국어로 번역하고 GeekNews 스타일로 요약

**Independent Test**: 영문 콘텐츠 입력 → title_ko, summary_ko, why_important 생성 확인

### Tests for User Story 3

- [x] T036 [P] [US3] Write unit tests for translator_tool in tests/unit/agent/domains/processor/test_translator_tool.py
- [x] T037 [P] [US3] Write unit tests for summarizer_tool in tests/unit/agent/domains/processor/test_summarizer_tool.py
- [x] T038 [US3] Write integration test for processing flow in tests/integration/test_processing_flow.py

### Implementation for User Story 3

- [x] T039 [US3] Create src/agent/domains/processor/__init__.py
- [x] T040 [US3] Create src/agent/domains/processor/tools/__init__.py
- [x] T041 [P] [US3] Implement translate tool in src/agent/domains/processor/tools/translator_tool.py
- [x] T042 [US3] Implement summarize tool in src/agent/domains/processor/tools/summarizer_tool.py (GeekNews 스타일)
- [x] T043 [US3] Implement JSON parsing retry logic in summarizer_tool.py

**Checkpoint**: 번역/요약 단독 테스트 가능

---

## Phase 6: User Story 4 - AX 관련성 스코어링 (Priority: P1)

**Goal**: 콘텐츠의 AX 관련성을 0.0~1.0 점수로 평가

**Independent Test**: 다양한 주제의 콘텐츠 → 일관된 relevance_score 산출 확인

### Tests for User Story 4

- [x] T044 [P] [US4] Write unit tests for scorer_tool in tests/unit/agent/domains/processor/test_scorer_tool.py

### Implementation for User Story 4

- [x] T045 [US4] Implement score_relevance tool in src/agent/domains/processor/tools/scorer_tool.py

**Checkpoint**: 스코어링 단독 테스트 가능

---

## Phase 7: User Story 5 - 슬랙 다이제스트 발송 (Priority: P1)

**Goal**: 처리된 콘텐츠를 슬랙 채널에 Block Kit 다이제스트로 발송

**Independent Test**: 처리된 콘텐츠 3건 → 슬랙 다이제스트 메시지 전송 확인

### Tests for User Story 5

- [x] T046 [P] [US5] Write unit tests for DigestRepository in tests/unit/repositories/test_digest_repo.py
- [x] T047 [P] [US5] Write unit tests for SubscriptionRepository in tests/unit/repositories/test_subscription_repo.py
- [x] T048 [P] [US5] Write unit tests for slack_sender_tool in tests/unit/agent/domains/distributor/test_slack_sender_tool.py (22 tests)
- [x] T049 [P] [US5] Write unit tests for DigestService in tests/unit/services/test_digest_service.py
- [ ] T050 [US5] Write integration test for distribution flow in tests/integration/test_distribution_flow.py

### Implementation for User Story 5

- [x] T051 [P] [US5] Implement DigestRepository in src/repositories/digest_repo.py
- [x] T052 [P] [US5] Implement SubscriptionRepository in src/repositories/subscription_repo.py
- [x] T053 [US5] Create src/agent/domains/distributor/__init__.py
- [x] T054 [US5] Create src/agent/domains/distributor/tools/__init__.py
- [x] T055 [US5] Implement slack_sender_tool in src/agent/domains/distributor/tools/slack_sender_tool.py
- [x] T056 [US5] Implement Block Kit message builder in slack_sender_tool.py
- [x] T057 [US5] Implement 50 blocks split logic in slack_sender_tool.py
- [x] T058 [US5] Implement DigestService in src/services/digest_service.py
- [x] T059 [US5] Implement digest_key duplication check in DigestService

**Checkpoint**: 다이제스트 발송 단독 테스트 가능

---

## Phase 8: User Story 6 - 스케줄러 기반 자동화 (Priority: P1)

**Goal**: Cloud Scheduler로 수집/배포 자동 트리거, OIDC 인증

**Independent Test**: /internal/collect, /internal/distribute 엔드포인트 호출 → 파이프라인 실행 확인

### Tests for User Story 6

- [x] T060 [P] [US6] Write unit tests for scheduler endpoints in tests/unit/api/test_scheduler.py
- [x] T061 [P] [US6] Write unit tests for internal_tasks endpoints in tests/unit/api/test_internal_tasks.py
- [x] T062 [P] [US6] Write unit tests for ContentPipeline in tests/unit/services/test_content_pipeline.py
- [x] T063 [P] [US6] Write unit tests for QualityFilter in tests/unit/services/test_quality_filter.py

### Implementation for User Story 6

- [x] T064 [US6] Implement ContentPipeline orchestrator in src/services/content_pipeline.py
- [x] T065 [US6] Implement QualityFilter in src/services/quality_filter.py
- [x] T066 [US6] Implement scheduler endpoints in src/api/scheduler.py
- [x] T067 [US6] Implement internal_tasks endpoints in src/api/internal_tasks.py
- [x] T068 [US6] Register scheduler and internal_tasks routers in src/api/main.py
- [ ] T069 [US6] Add OIDC token verification middleware (optional for MVP, document for prod)

**Checkpoint**: 전체 파이프라인 E2E 테스트 가능

---

## Phase 9: User Story 7 - 콘텐츠 소스 관리 (Priority: P2)

**Goal**: 소스 CRUD API 제공

**Independent Test**: API로 소스 등록/조회/수정/삭제 → Firestore 반영 확인

### Tests for User Story 7

- [x] T070 [P] [US7] Write unit tests for sources API in tests/unit/api/test_sources.py

### Implementation for User Story 7

- [x] T071 [US7] Implement sources CRUD endpoints in src/api/sources.py
- [x] T072 [US7] Register sources router in src/api/main.py

**Checkpoint**: 소스 관리 API 단독 테스트 가능

---

## Phase 10: User Story 8 - 구독 관리 (Priority: P2)

**Goal**: 구독 CRUD API 제공

**Independent Test**: API로 구독 등록/조회/수정/삭제 → Firestore 반영 확인

### Tests for User Story 8

- [x] T073 [P] [US8] Write unit tests for subscriptions API in tests/unit/api/test_subscriptions.py

### Implementation for User Story 8

- [x] T074 [US8] Implement subscriptions CRUD endpoints in src/api/subscriptions.py
- [x] T075 [US8] Register subscriptions router in src/api/main.py

**Checkpoint**: 구독 관리 API 단독 테스트 가능

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: 통합 검증 및 품질 개선

- [x] T076 Run full test suite and ensure 80%+ coverage (320 tests passed)
- [x] T077 [P] Run ruff check and fix all issues
- [x] T078 [P] Run mypy and fix all type errors (Pydantic plugin 추가)
- [x] T079 [P] Update CLAUDE.md with Phase 1 implementation status
- [x] T080 Run quickstart.md validation (manual end-to-end test)
- [x] T081 Document environment variables in .env.example

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ──────────────────────────────────────────────────────────►
         │
         ▼
Phase 2: Foundational (BLOCKS ALL USER STORIES) ─────────────────────────►
         │
         ├───────────┬───────────┬───────────┬───────────┬───────────┐
         ▼           ▼           ▼           ▼           ▼           ▼
      Phase 3    Phase 4    Phase 5    Phase 6    Phase 7    Phase 8
       (US1)      (US2)      (US3)      (US4)      (US5)      (US6)
        P1         P1         P1         P1         P1         P1
         │           │           │           │           │           │
         └───────────┴───────────┴───────────┴───────────┴───────────┘
                                      │
                      ┌───────────────┴───────────────┐
                      ▼                               ▼
                  Phase 9 (US7) P2              Phase 10 (US8) P2
                      │                               │
                      └───────────────┬───────────────┘
                                      ▼
                              Phase 11: Polish
```

### User Story Dependencies

- **US1 (RSS 수집)**: Foundational 완료 후 시작 가능
- **US2 (YouTube 수집)**: Foundational 완료 후 시작 가능, US1과 병렬 가능
- **US3 (번역/요약)**: US1 또는 US2 완료 필요 (콘텐츠 입력)
- **US4 (스코어링)**: US3 완료 필요 (요약 결과 입력)
- **US5 (다이제스트)**: US4 완료 필요 (스코어링 결과)
- **US6 (스케줄러)**: US1~US5 통합, 모든 P1 완료 후 통합 테스트
- **US7 (소스 관리)**: US1 완료 후 가능 (SourceRepository 재사용)
- **US8 (구독 관리)**: US5 완료 후 가능 (SubscriptionRepository 재사용)

### Parallel Opportunities

**Phase 2 내부**:
```bash
# 모든 모델 테스트 병렬 실행
T010, T011, T012, T013  # 병렬

# 모든 모델 구현 병렬 실행
T014, T015, T016, T017  # 병렬
```

**Phase 3~6 (P1 User Stories)**:
```bash
# US1, US2는 독립적으로 병렬 가능
Phase 3 (US1) || Phase 4 (US2)

# US3, US4, US5, US6는 순차 의존성
Phase 5 → Phase 6 → Phase 7 → Phase 8
```

---

## Parallel Example: Foundational Phase

```bash
# Launch all model tests in parallel:
Task T010: "Write tests for Source model"
Task T011: "Write tests for Content model"
Task T012: "Write tests for Subscription model"
Task T013: "Write tests for Digest model"

# After tests, launch all implementations in parallel:
Task T014: "Implement Source model"
Task T015: "Implement Content model"
Task T016: "Implement Subscription model"
Task T017: "Implement Digest model"
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3 + US4 + US5 + US6)

1. Phase 1: Setup 완료
2. Phase 2: Foundational 완료 (CRITICAL - 모든 Story 차단)
3. Phase 3-8: P1 User Stories 순차 완료
4. **STOP and VALIDATE**: 전체 파이프라인 E2E 테스트
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (RSS 수집) → 수집만 테스트 가능
3. US2 (YouTube 수집) → 두 종류 수집 테스트 가능
4. US3 + US4 (처리) → 번역/요약/스코어링 테스트 가능
5. US5 (배포) → 다이제스트 발송 테스트 가능
6. US6 (통합) → 전체 자동화 파이프라인 완성 🎉
7. US7, US8 (관리 API) → 운영 편의성 향상

---

## Summary

| 구분 | 태스크 수 |
|------|----------|
| Phase 1: Setup | 9 |
| Phase 2: Foundational | 15 |
| Phase 3: US1 (RSS) | 9 |
| Phase 4: US2 (YouTube) | 2 |
| Phase 5: US3 (번역/요약) | 8 |
| Phase 6: US4 (스코어링) | 2 |
| Phase 7: US5 (다이제스트) | 14 |
| Phase 8: US6 (스케줄러) | 10 |
| Phase 9: US7 (소스 관리) | 3 |
| Phase 10: US8 (구독 관리) | 3 |
| Phase 11: Polish | 6 |
| **Total** | **81** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Constitution 준수: Test-First (테스트 먼저 작성)
- 각 Checkpoint에서 해당 기능 단독 테스트 가능
- 커밋은 태스크 단위 또는 논리적 그룹 단위로
