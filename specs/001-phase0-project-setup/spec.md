# Feature Specification: Phase 0 - 프로젝트 초기화 및 Cognee 통합

**Feature Branch**: `001-phase0-project-setup`
**Created**: 2025-12-26
**Status**: Draft
**Input**: docs/ax-content-hub-plan.md Phase 0 섹션

## Clarifications (Resolved)

| 질문 | 결정 | 근거 |
|------|------|------|
| geniefy 참조 방식 | 새로 작성 | geniefy 패턴을 참고하되 프로젝트에 맞게 최적화 |
| Cognee 로컬 설정 | LanceDB 로컬 | Cognee 기본 설정, 별도 인프라 불필요 |
| 테스트 범위 | 단위 테스트만 | Phase 0는 인프라 설정, 통합 테스트는 Phase 1에서 |
| Docker Compose | Firestore만 | 최소 구성으로 시작, 필요시 확장 |

## User Scenarios & Testing

### User Story 1 - 개발 환경 설정 (Priority: P1)

개발자가 프로젝트를 클론한 후 `uv sync` 한 번으로 모든 의존성을 설치하고,
로컬에서 Firestore 에뮬레이터와 함께 개발 서버를 실행할 수 있다.

**Why this priority**: 모든 후속 개발의 기반이 되는 필수 인프라

**Independent Test**: `uv sync && docker compose up -d && uv run uvicorn src.api.main:app --reload`로 서버 시작 후 `/health` 엔드포인트 응답 확인

**Acceptance Scenarios**:

1. **Given** 프로젝트가 클론된 상태, **When** `uv sync --all-extras` 실행, **Then** 모든 의존성이 설치됨
2. **Given** 의존성 설치 완료, **When** `docker compose up -d` 실행, **Then** Firestore 에뮬레이터가 실행됨
3. **Given** 에뮬레이터 실행 중, **When** 개발 서버 시작, **Then** `/health` 엔드포인트가 200 OK 반환

---

### User Story 2 - 설정 관리 (Priority: P1)

환경 변수를 통해 GCP 프로젝트 ID, Gemini API 키, Slack 토큰 등을 설정하고,
Pydantic Settings로 타입 안전하게 접근할 수 있다.

**Why this priority**: 모든 외부 서비스 연동의 기반

**Independent Test**: 환경 변수 설정 후 `settings.GCP_PROJECT_ID` 등 접근 시 올바른 값 반환

**Acceptance Scenarios**:

1. **Given** `.env` 파일에 `GCP_PROJECT_ID=test-project`, **When** `Settings()` 인스턴스 생성, **Then** `settings.GCP_PROJECT_ID == "test-project"`
2. **Given** 필수 환경 변수 누락, **When** `Settings()` 인스턴스 생성, **Then** `ValidationError` 발생
3. **Given** 환경 변수 설정 완료, **When** 애플리케이션 시작, **Then** 모든 설정이 로깅됨 (민감 정보 마스킹)

---

### User Story 3 - 구조화된 로깅 (Priority: P1)

structlog를 사용하여 JSON 형식의 구조화된 로그를 출력하고,
요청별 컨텍스트(request_id, user_id 등)를 자동으로 포함한다.

**Why this priority**: 운영 환경에서의 디버깅 및 모니터링 필수

**Independent Test**: 로그 출력 시 JSON 형식으로 `request_id`, `timestamp`, `level` 필드 포함 확인

**Acceptance Scenarios**:

1. **Given** structlog 설정 완료, **When** `logger.info("test")` 호출, **Then** JSON 형식 로그 출력
2. **Given** 로거 컨텍스트에 `request_id` 바인딩, **When** 로그 출력, **Then** `request_id` 필드 포함
3. **Given** 에러 발생, **When** `logger.exception()` 호출, **Then** 스택 트레이스가 구조화되어 포함

---

### User Story 4 - Firestore 클라이언트 (Priority: P1)

Firestore에 CRUD 작업을 수행할 수 있는 클라이언트를 제공하고,
로컬 에뮬레이터와 프로덕션 환경을 자동으로 구분한다.

**Why this priority**: 모든 데이터 저장의 기반

**Independent Test**: 에뮬레이터에서 문서 생성/조회/수정/삭제 후 결과 확인

**Acceptance Scenarios**:

1. **Given** 에뮬레이터 실행 중, **When** 문서 생성, **Then** 문서가 저장됨
2. **Given** 문서 존재, **When** 문서 조회, **Then** 올바른 데이터 반환
3. **Given** `FIRESTORE_EMULATOR_HOST` 환경 변수 설정, **When** 클라이언트 초기화, **Then** 에뮬레이터에 연결

---

### User Story 5 - Cognee 메모리 도구 통합 (Priority: P2)

Google ADK 에이전트에서 Cognee의 `add_memory`와 `search_memory` 도구를 사용하여
지식을 저장하고 검색할 수 있다.

**Why this priority**: AI 에이전트의 지속적 메모리 기능 제공 (Phase 1 에이전트 개발에 필요)

**Independent Test**: `add_memory`로 정보 저장 후 `search_memory`로 검색 시 결과 반환

**Acceptance Scenarios**:

1. **Given** Cognee 도구 초기화, **When** `add_memory("AI 트렌드 2024")` 호출, **Then** 메모리에 저장됨
2. **Given** 메모리에 정보 저장됨, **When** `search_memory("AI 트렌드")` 호출, **Then** 관련 정보 반환
3. **Given** workspace_id 지정, **When** 도구 초기화, **Then** 세션별 격리된 메모리 사용

---

### User Story 6 - Slack 클라이언트 (Priority: P2)

Slack API를 통해 메시지를 전송할 수 있는 클라이언트를 제공한다.

**Why this priority**: Phase 1 다이제스트 발송에 필요

**Independent Test**: 테스트 채널에 메시지 전송 후 Slack에서 확인

**Acceptance Scenarios**:

1. **Given** 유효한 Slack 토큰, **When** `chat_postMessage` 호출, **Then** 메시지 전송됨
2. **Given** Block Kit 메시지, **When** 전송, **Then** 포맷팅된 메시지 표시
3. **Given** 잘못된 채널 ID, **When** 메시지 전송, **Then** 적절한 에러 반환

---

### User Story 7 - Cloud Tasks 클라이언트 (Priority: P2)

비동기 작업을 Cloud Tasks 큐에 추가하고, 로컬에서는 직접 실행 모드로 동작한다.

**Why this priority**: Phase 1 비동기 파이프라인에 필요

**Independent Test**: 로컬 모드에서 태스크 추가 시 즉시 실행 확인

**Acceptance Scenarios**:

1. **Given** `TASKS_MODE=direct`, **When** 태스크 추가, **Then** 즉시 동기 실행
2. **Given** `TASKS_MODE=cloud_tasks`, **When** 태스크 추가, **Then** Cloud Tasks 큐에 추가됨
3. **Given** 태스크 실패, **When** 재시도 정책 적용, **Then** 지정된 횟수만큼 재시도

---

### User Story 8 - FastAPI 앱 라이프사이클 (Priority: P1)

FastAPI 앱이 시작/종료 시 리소스를 올바르게 초기화/정리하고,
헬스체크 엔드포인트를 제공한다.

**Why this priority**: 안정적인 서버 운영의 기반

**Independent Test**: 앱 시작/종료 시 로그 확인, `/health` 엔드포인트 응답 확인

**Acceptance Scenarios**:

1. **Given** 앱 시작, **When** lifespan 컨텍스트 진입, **Then** 클라이언트들 초기화됨
2. **Given** 앱 종료, **When** lifespan 컨텍스트 종료, **Then** 리소스 정리됨
3. **Given** 앱 실행 중, **When** `GET /health` 요청, **Then** `{"status": "healthy"}` 반환

---

### Edge Cases

- Firestore 에뮬레이터가 실행되지 않은 상태에서 연결 시도 시 명확한 에러 메시지
- 환경 변수 타입이 잘못된 경우 (예: 포트 번호에 문자열) 상세한 검증 에러
- Cognee 서비스 불가 시 graceful degradation (로깅만 하고 에러 미전파)
- Slack API rate limit 도달 시 적절한 대기 및 재시도

## Requirements

### Functional Requirements

- **FR-001**: 시스템 MUST `uv sync --all-extras`로 모든 의존성 설치 가능
- **FR-002**: 시스템 MUST Pydantic Settings로 환경 변수 관리 제공
- **FR-003**: 시스템 MUST structlog로 JSON 구조화된 로깅 제공
- **FR-004**: 시스템 MUST Firestore CRUD 클라이언트 제공
- **FR-005**: 시스템 MUST Cognee 메모리 도구 (add_memory, search_memory) 통합
- **FR-006**: 시스템 MUST Slack 메시지 전송 클라이언트 제공
- **FR-007**: 시스템 MUST Cloud Tasks 비동기 작업 클라이언트 제공
- **FR-008**: 시스템 MUST FastAPI 앱 lifespan 관리 제공
- **FR-009**: 시스템 MUST `/health` 헬스체크 엔드포인트 제공
- **FR-010**: 시스템 MUST pre-commit hooks 설정 제공

### Key Entities

- **Settings**: 애플리케이션 설정 (환경 변수 매핑)
- **FirestoreClient**: Firestore 데이터베이스 클라이언트
- **SlackClient**: Slack API 클라이언트
- **TasksClient**: Cloud Tasks 클라이언트
- **CogneeTools**: Cognee 메모리 도구 래퍼

## Success Criteria

### Measurable Outcomes

- **SC-001**: `uv sync && uv run pytest` 실행 시 모든 테스트 통과
- **SC-002**: 개발 서버 시작 후 5초 이내에 `/health` 응답
- **SC-003**: Firestore 에뮬레이터 CRUD 작업 100% 성공
- **SC-004**: structlog 로그에 request_id 포함률 100%
- **SC-005**: pre-commit hooks가 모든 커밋에서 실행됨
