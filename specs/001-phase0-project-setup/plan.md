# Implementation Plan: Phase 0 - 프로젝트 초기화 및 Cognee 통합

**Branch**: `001-phase0-project-setup` | **Date**: 2025-12-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-phase0-project-setup/spec.md`

## Summary

Phase 0는 AX Content Hub 프로젝트의 개발 환경과 핵심 인프라를 구축합니다.
geniefy-slack-agent 패턴을 참고하여 Settings, 로깅, Firestore/Slack/Tasks 클라이언트를 새로 작성하고,
Google ADK 에이전트를 위한 Cognee 메모리 도구를 통합합니다.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, google-adk, cognee, cognee-integration-google-adk, structlog, pydantic-settings
**Storage**: Google Firestore (로컬: 에뮬레이터)
**Testing**: pytest (단위 테스트만, Phase 0 범위)
**Target Platform**: Linux server (Cloud Run), 로컬 개발 (macOS/Linux)
**Project Type**: single
**Performance Goals**: 서버 시작 5초 이내, `/health` 응답 100ms 이내
**Constraints**: uv만 사용 (poetry/pip 금지), 절대 임포트 강제
**Scale/Scope**: 단일 서비스, Phase 1 MVP 지원

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 원칙 | 준수 여부 | 비고 |
|------|-----------|------|
| I. Test-First | ✅ PASS | 각 클라이언트/설정에 단위 테스트 작성 |
| II. API-First | ✅ PASS | `/health` 엔드포인트 스키마 우선 정의 |
| III. Korean-First | N/A | Phase 0는 사용자 대면 없음 |
| IV. Quality Gates | ✅ PASS | pre-commit, Ruff, MyPy 설정 포함 |
| V. Simplicity | ✅ PASS | 최소 필수 모듈만 구현 |

## Project Structure

### Documentation (this feature)

```text
specs/001-phase0-project-setup/
├── spec.md              # 기능 명세
├── plan.md              # 이 파일
└── tasks.md             # Phase 4에서 생성
```

### Source Code (repository root)

```text
src/
├── api/
│   └── main.py              # FastAPI 앱 + lifespan + /health
│
├── config/
│   ├── __init__.py
│   ├── settings.py          # Pydantic Settings (환경 변수)
│   └── logging.py           # structlog 설정
│
├── adapters/
│   ├── __init__.py
│   ├── firestore_client.py  # Firestore CRUD 클라이언트
│   ├── slack_client.py      # Slack API 클라이언트
│   └── tasks_client.py      # Cloud Tasks 클라이언트
│
└── agent/
    └── core/
        ├── __init__.py
        └── cognee_tools.py  # Cognee 메모리 도구 래퍼

tests/
└── unit/
    ├── config/
    │   ├── test_settings.py
    │   └── test_logging.py
    ├── adapters/
    │   ├── test_firestore_client.py
    │   ├── test_slack_client.py
    │   └── test_tasks_client.py
    └── agent/
        └── test_cognee_tools.py

# 루트 파일
docker-compose.yml           # Firestore 에뮬레이터
conftest.py                  # pytest 공통 fixtures
```

**Structure Decision**: Single project 구조. `src/` 하위에 도메인별 모듈 배치.
Phase 1에서 `src/agent/domains/`에 수집/처리/배포 에이전트 추가 예정.

## Key Design Decisions

### 1. Settings 관리 (Pydantic Settings)

```python
# src/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # GCP
    GCP_PROJECT_ID: str
    FIRESTORE_EMULATOR_HOST: str | None = None

    # Gemini
    GOOGLE_API_KEY: str

    # Slack
    SLACK_BOT_TOKEN: str
    SLACK_SIGNING_SECRET: str

    # Cloud Tasks
    TASKS_MODE: str = "direct"  # direct | cloud_tasks
    TASKS_TARGET_URL: str | None = None
    TASKS_SERVICE_ACCOUNT_EMAIL: str | None = None

    @property
    def is_local(self) -> bool:
        return self.FIRESTORE_EMULATOR_HOST is not None
```

### 2. structlog 로깅

```python
# src/config/logging.py
import structlog

def configure_logging(json_logs: bool = True) -> None:
    """structlog 설정"""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(processors=processors)
```

### 3. Firestore 클라이언트

```python
# src/adapters/firestore_client.py
from google.cloud import firestore
from src.config.settings import Settings

class FirestoreClient:
    def __init__(self, settings: Settings):
        self._client = firestore.Client(project=settings.GCP_PROJECT_ID)

    async def get(self, collection: str, doc_id: str) -> dict | None: ...
    async def set(self, collection: str, doc_id: str, data: dict) -> None: ...
    async def update(self, collection: str, doc_id: str, data: dict) -> None: ...
    async def delete(self, collection: str, doc_id: str) -> None: ...
    async def query(self, collection: str, filters: list) -> list[dict]: ...
```

### 4. Cognee 메모리 도구

```python
# src/agent/core/cognee_tools.py
from cognee_integration_google_adk import add_tool, search_tool, get_sessionized_cognee_tools

def get_cognee_tools(workspace_id: str | None = None):
    """Cognee 메모리 도구 반환

    Args:
        workspace_id: 세션 ID (멀티 워크스페이스용)

    Returns:
        (add_memory, search_memory) 튜플
    """
    if workspace_id:
        return get_sessionized_cognee_tools(workspace_id)
    return add_tool, search_tool
```

### 5. FastAPI Lifespan

```python
# src/api/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    configure_logging()
    app.state.settings = Settings()
    app.state.firestore = FirestoreClient(app.state.settings)
    logger.info("Application started")

    yield

    # Shutdown
    logger.info("Application shutting down")

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

## Dependencies

```toml
# pyproject.toml 추가 의존성
[project.dependencies]
fastapi = ">=0.115"
uvicorn = {extras = ["standard"], version = ">=0.32"}
pydantic-settings = ">=2.6"
structlog = ">=24.4"
google-cloud-firestore = ">=2.19"
google-cloud-tasks = ">=2.16"
slack-sdk = ">=3.33"
cognee = ">=0.1"
cognee-integration-google-adk = ">=0.1"

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-cov>=6.0",
    "ruff>=0.8",
    "mypy>=1.13",
    "pre-commit>=4.0",
]
```

## Complexity Tracking

> 헌법 위반 없음. 최소 필수 모듈만 구현.

| 결정 | 근거 | 대안 검토 |
|------|------|-----------|
| 단일 프로젝트 구조 | Phase 0는 인프라 설정만, 모노레포 불필요 | 멀티 패키지는 Phase 3+ 확장 시 검토 |
| 동기 Firestore | google-cloud-firestore가 동기 기본 | 필요시 AsyncIO 래퍼 추가 |
| LanceDB 기본 | Cognee 기본 설정, 별도 인프라 불필요 | Qdrant는 Phase 3+ 프로덕션에서 검토 |
