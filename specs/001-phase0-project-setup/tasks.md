# Tasks: Phase 0 - 프로젝트 초기화 및 Cognee 통합

**Input**: Design documents from `/specs/001-phase0-project-setup/`
**Prerequisites**: plan.md (required), spec.md (required)

**Tests**: 단위 테스트만 포함 (Phase 0 범위)

**Organization**: User Story 기반으로 그룹화, 독립적 구현/테스트 가능

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, etc.)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 프로젝트 구조 및 기본 설정

- [ ] T001 프로젝트 디렉토리 구조 생성 (`src/`, `tests/`, 하위 패키지)
- [ ] T002 pyproject.toml 의존성 업데이트 (fastapi, structlog, cognee 등)
- [ ] T003 [P] docker-compose.yml 생성 (Firestore 에뮬레이터)
- [ ] T004 [P] conftest.py 생성 (pytest 공통 fixtures)
- [ ] T005 [P] .env.example 생성 (환경 변수 템플릿)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 User Story에 필요한 핵심 인프라

**⚠️ CRITICAL**: 이 Phase 완료 전까지 User Story 작업 불가

### Tests for Foundational ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T006 [P] tests/unit/config/test_settings.py 작성
- [ ] T007 [P] tests/unit/config/test_logging.py 작성

### Implementation for Foundational

- [ ] T008 [US2] src/config/settings.py 구현 (Pydantic Settings)
- [ ] T009 [US3] src/config/logging.py 구현 (structlog 설정)
- [ ] T010 src/config/__init__.py 생성 (모듈 export)

**Checkpoint**: Settings + Logging 완료, 테스트 통과

---

## Phase 3: User Story 4 - Firestore 클라이언트 (Priority: P1)

**Goal**: Firestore CRUD 클라이언트 제공

**Independent Test**: 에뮬레이터에서 문서 생성/조회/수정/삭제 확인

### Tests for User Story 4 ⚠️

- [ ] T011 tests/unit/adapters/test_firestore_client.py 작성

### Implementation for User Story 4

- [ ] T012 [US4] src/adapters/firestore_client.py 구현
- [ ] T013 [US4] src/adapters/__init__.py 생성 (모듈 export)

**Checkpoint**: Firestore 클라이언트 완료, 단위 테스트 통과

---

## Phase 4: User Story 6 - Slack 클라이언트 (Priority: P2)

**Goal**: Slack 메시지 전송 클라이언트 제공

**Independent Test**: Mock으로 chat_postMessage 호출 검증

### Tests for User Story 6 ⚠️

- [ ] T014 tests/unit/adapters/test_slack_client.py 작성

### Implementation for User Story 6

- [ ] T015 [US6] src/adapters/slack_client.py 구현

**Checkpoint**: Slack 클라이언트 완료, 단위 테스트 통과

---

## Phase 5: User Story 7 - Cloud Tasks 클라이언트 (Priority: P2)

**Goal**: 비동기 작업 큐 클라이언트 제공

**Independent Test**: direct 모드에서 즉시 실행 확인

### Tests for User Story 7 ⚠️

- [ ] T016 tests/unit/adapters/test_tasks_client.py 작성

### Implementation for User Story 7

- [ ] T017 [US7] src/adapters/tasks_client.py 구현

**Checkpoint**: Tasks 클라이언트 완료, 단위 테스트 통과

---

## Phase 6: User Story 5 - Cognee 메모리 도구 (Priority: P2)

**Goal**: ADK 에이전트용 Cognee 메모리 도구 래퍼

**Independent Test**: add_memory/search_memory 호출 검증

### Tests for User Story 5 ⚠️

- [ ] T018 tests/unit/agent/test_cognee_tools.py 작성

### Implementation for User Story 5

- [ ] T019 [US5] src/agent/core/cognee_tools.py 구현
- [ ] T020 [US5] src/agent/core/__init__.py 생성
- [ ] T021 [US5] src/agent/__init__.py 생성

**Checkpoint**: Cognee 도구 완료, 단위 테스트 통과

---

## Phase 7: User Story 8 - FastAPI 앱 (Priority: P1)

**Goal**: FastAPI 앱 + lifespan + /health 엔드포인트

**Independent Test**: 앱 시작 후 /health 응답 확인

### Tests for User Story 8 ⚠️

- [ ] T022 tests/unit/api/test_main.py 작성 (TestClient 사용)

### Implementation for User Story 8

- [ ] T023 [US8] src/api/main.py 구현 (lifespan, /health)
- [ ] T024 [US8] src/api/__init__.py 생성

**Checkpoint**: FastAPI 앱 완료, /health 테스트 통과

---

## Phase 8: User Story 1 - 개발 환경 통합 (Priority: P1)

**Goal**: 전체 개발 환경 통합 및 검증

**Independent Test**: `uv sync && docker compose up -d && uv run uvicorn` 성공

### Integration Tasks

- [ ] T025 [US1] .pre-commit-config.yaml 업데이트 (ruff, mypy)
- [ ] T026 [US1] uv sync --all-extras 실행 및 검증
- [ ] T027 [US1] docker compose up -d && 서버 시작 통합 테스트
- [ ] T028 [US1] 전체 테스트 실행 (uv run pytest tests/ -v)

**Checkpoint**: 개발 환경 완전 설정, 모든 테스트 통과

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 문서화 및 마무리

- [ ] T029 [P] CLAUDE.md 업데이트 (Phase 0 완료 반영)
- [ ] T030 [P] README.md 빠른 시작 섹션 업데이트
- [ ] T031 전체 Quality Gates 통과 확인 (ruff, mypy, pytest)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Setup (Phase 1)
    ↓
Foundational (Phase 2) ← BLOCKS ALL USER STORIES
    ↓
┌───────────────┬───────────────┬───────────────┬───────────────┐
│ Firestore(P3) │ Slack(P4)     │ Tasks(P5)     │ Cognee(P6)    │
│ US4, P1       │ US6, P2       │ US7, P2       │ US5, P2       │
└───────────────┴───────────────┴───────────────┴───────────────┘
    ↓ (all adapters complete)
FastAPI App (Phase 7) - US8, P1
    ↓
Integration (Phase 8) - US1, P1
    ↓
Polish (Phase 9)
```

### Within Each User Story

1. 테스트 작성 → 실패 확인 (Red)
2. 구현 (Green)
3. 리팩토링 (Refactor)
4. Checkpoint 검증

### Parallel Opportunities

- T003, T004, T005: Setup 태스크 병렬 실행 가능
- T006, T007: Foundational 테스트 병렬 실행 가능
- Phase 3-6: 모든 어댑터/도구는 Foundational 완료 후 병렬 가능
- T029, T030: Polish 문서화 병렬 가능

---

## Task Count Summary

| Phase | 태스크 수 | 테스트 수 | 구현 수 |
|-------|----------|----------|---------|
| Setup | 5 | 0 | 5 |
| Foundational | 5 | 2 | 3 |
| Firestore | 3 | 1 | 2 |
| Slack | 2 | 1 | 1 |
| Tasks | 2 | 1 | 1 |
| Cognee | 4 | 1 | 3 |
| FastAPI | 3 | 1 | 2 |
| Integration | 4 | 0 | 4 |
| Polish | 3 | 0 | 3 |
| **Total** | **31** | **7** | **24** |

---

## Notes

- [P] 태스크 = 병렬 실행 가능
- [US#] 라벨 = User Story 매핑
- 각 Checkpoint에서 테스트 통과 확인 후 다음 Phase 진행
- Constitution Check: Test-First 원칙 준수 (테스트 → 구현 순서)
