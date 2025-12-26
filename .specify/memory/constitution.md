<!--
Sync Impact Report
==================
Version: 0.0.0 → 1.0.0 (MAJOR - initial constitution)

Added Principles:
- I. Test-First (NON-NEGOTIABLE)
- II. API-First Design
- III. Korean-First Communication
- IV. Quality Gates
- V. Simplicity

Added Sections:
- Technology Standards (Python 3.12+, uv, Ruff)
- Development Workflow (pre-commit, code review)
- Governance (amendment procedure, versioning)

Templates Updated:
- ✅ plan-template.md (Constitution Check section compatible)
- ✅ spec-template.md (User stories align with TDD principle)
- ✅ tasks-template.md (Test-first workflow compatible)

Follow-up TODOs: None
-->

# AX Content Hub Constitution

## Core Principles

### I. Test-First (NON-NEGOTIABLE)

모든 주요 기능은 테스트 코드를 먼저 작성한 후 구현합니다.

- 테스트 작성 → 실패 확인(Red) → 구현(Green) → 리팩토링(Refactor) 사이클 준수
- 테스트 없이 PR 머지 금지 (핵심 비즈니스 로직 대상)
- Contract 테스트로 API 경계 검증, Integration 테스트로 에이전트 동작 검증
- 테스트는 문서이자 스펙: 테스트 코드만 보고 기능을 이해할 수 있어야 함

**근거**: 에이전트 기반 시스템은 예측하기 어려운 동작이 발생할 수 있으며, 테스트가 유일한 안전장치입니다.

### II. API-First Design

외부 인터페이스(API, Slack 메시지 포맷)를 먼저 정의하고 구현합니다.

- FastAPI 엔드포인트: OpenAPI 스펙 우선 정의
- Slack 메시지: Block Kit 구조 우선 설계
- 에이전트 도구: 입출력 스키마 Pydantic 모델로 명시
- 변경 시 하위 호환성 유지 또는 버전 분리

**근거**: 콘텐츠 허브는 외부 서비스(Slack, RSS, YouTube)와 통신하므로 인터페이스 명세가 핵심입니다.

### III. Korean-First Communication

모든 사용자 대면 콘텐츠와 에이전트 응답은 한국어를 기본으로 합니다.

- Slack 다이제스트: 한국어로 요약 및 발송
- 에이전트 응답: 한국어로 생성
- GeekNews 스타일: 제목 20자 이내, 요약 3문장 이내
- 영문 원문은 링크로 제공, 번역본 우선 표시

**근거**: 타겟 사용자는 한국어 사용자이며, "읽어야 할 것"이 아닌 "이미 정리된 것"을 받는 경험이 핵심 가치입니다.

### IV. Quality Gates

코드 품질 도구를 통과하지 않으면 머지할 수 없습니다.

- Ruff: 린팅 + 포맷팅 + import 정렬 (zero warnings)
- MyPy: 타입 체크 통과 필수
- pytest: 테스트 전체 통과 필수
- pre-commit: 커밋 시 자동 검사 활성화 필수

**근거**: 자동화된 품질 검사는 코드 리뷰 부담을 줄이고 일관된 코드베이스를 유지합니다.

### V. Simplicity

필요한 것만 구현하고, 과도한 추상화를 피합니다.

- YAGNI 원칙: 현재 필요하지 않은 기능은 구현하지 않음
- 3개 이상 반복되기 전까지 추상화 금지
- 단일 책임 원칙: 하나의 모듈은 하나의 역할만 수행
- 복잡도 정당화 필수: Constitution Check에서 위반 시 근거 명시

**근거**: 에이전트 기반 시스템은 이미 충분히 복잡하므로 코드 레벨에서 단순성을 유지해야 합니다.

## Technology Standards

이 프로젝트의 기술 스택과 제약 조건을 명시합니다.

- **언어**: Python 3.12+
- **패키지 관리**: uv (poetry, pip 사용 금지)
- **웹 프레임워크**: FastAPI
- **에이전트**: Google ADK + Cognee
- **LLM**: Gemini (gemini-3-flash-preview)
- **데이터베이스**: Google Firestore
- **인프라**: Google Cloud (Cloud Run, Cloud Scheduler, Cloud Tasks)
- **코드 품질**: Ruff (black, isort 대체), MyPy
- **임포트 규칙**: 절대 임포트만 허용 (`from src.models import ...`)

## Development Workflow

개발 프로세스와 협업 규칙을 정의합니다.

- **브랜치 전략**: main 브랜치 보호, feature 브랜치에서 작업
- **커밋 컨벤션**: Conventional Commits 형식 권장
- **pre-commit**: 최초 설정 시 `uv run pre-commit install` 실행 필수
- **코드 리뷰**: 셀프 머지 허용, 단 Quality Gates 통과 필수
- **문서화**: CLAUDE.md 최신 상태 유지, 주요 변경 시 업데이트

## Governance

헌법은 프로젝트의 모든 관행보다 우선합니다.

- **수정 절차**: 헌법 수정 시 PR에 변경 사유와 영향 분석 포함 필수
- **버전 관리**:
  - MAJOR: 원칙 삭제 또는 재정의 (하위 호환성 파괴)
  - MINOR: 원칙 추가 또는 섹션 확장
  - PATCH: 문구 수정, 오타 수정, 명확화
- **준수 검증**: 모든 PR은 Constitution Check 섹션에서 원칙 준수 확인
- **런타임 가이드**: 상세 개발 지침은 CLAUDE.md 참조

**Version**: 1.0.0 | **Ratified**: 2025-12-26 | **Last Amended**: 2025-12-26
