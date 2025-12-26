# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

AX(AI Transformation) 콘텐츠를 큐레이션하여 슬랙으로 전달하는 봇입니다.

**핵심 가치**: "읽어야 할 것"이 아니라 "이미 정리된 것"을 받는 경험

**주요 파이프라인**:
- **수집(Collect)**: RSS, YouTube 자막, 웹 스크래핑
- **처리(Process)**: 번역, GeekNews 스타일 요약, AX 관련성 스코어링
- **배포(Distribute)**: 슬랙 다이제스트 발송

**기술 스택**:
- Python 3.12 + uv / FastAPI / Google ADK + Cognee
- Google Cloud: Firestore, Cloud Run, Cloud Scheduler, Cloud Tasks
- LLM: Gemini (gemini-3-flash-preview)

## 주요 명령어

```bash
# 의존성 설치
uv sync --all-extras

# Docker로 Firestore 에뮬레이터 시작
docker compose up -d

# 개발 서버 시작
uv run uvicorn src.api.main:app --reload --port 8080

# 테스트
uv run pytest tests/ -v
uv run pytest --cov=src tests/  # 커버리지 포함

# 코드 품질 (Ruff로 통합)
uv run ruff check --fix src/ tests/   # 린팅 (자동 수정)
uv run ruff format src/ tests/         # 포맷팅
uv run mypy src/                        # 타입 체크

# pre-commit 설정
uv run pre-commit install              # Git hooks 설치 (최초 1회)
uv run pre-commit run --all-files      # 전체 파일 검사
```

## 현재 구현 상태

**Phase 0 완료** - 프로젝트 초기화 및 기반 인프라

| 구성요소 | 상태 | 설명 |
|----------|------|------|
| Settings | ✅ | Pydantic Settings 기반 환경 설정 |
| Logging | ✅ | structlog JSON 로깅 |
| Firestore | ✅ | CRUD 클라이언트 (에뮬레이터 지원) |
| Slack | ✅ | 메시지 전송 클라이언트 |
| Tasks | ✅ | Cloud Tasks / direct 모드 |
| Cognee | ✅ | 메모리 도구 래퍼 (지연 로딩) |
| FastAPI | ✅ | /health 엔드포인트 |
| CI/CD | ✅ | GitHub Actions (ruff, mypy, pytest) |

## 프로젝트 구조

```
src/
├── api/                        # FastAPI 앱
│   └── main.py                 # lifespan, /health ✅
│
├── agent/                      # Google ADK 에이전트
│   └── core/
│       └── cognee_tools.py     # Cognee 메모리 도구 ✅
│
├── adapters/                   # 외부 서비스 클라이언트
│   ├── firestore_client.py     # ✅
│   ├── slack_client.py         # ✅
│   └── tasks_client.py         # ✅
│
└── config/
    ├── settings.py             # Pydantic Settings ✅
    └── logging.py              # structlog ✅

tests/
├── conftest.py                 # 공통 fixtures
└── unit/
    ├── adapters/               # 어댑터 테스트 (30 tests)
    ├── agent/
    ├── api/
    └── config/
```

### 향후 구현 예정 (Phase 1+)

```
src/
├── agent/
│   ├── content_hub_agent.py    # 메인 오케스트레이터
│   └── domains/
│       ├── collector/          # 수집 에이전트
│       ├── processor/          # 처리 에이전트
│       └── distributor/        # 배포 에이전트
│
├── services/                   # 비즈니스 로직
├── models/                     # Pydantic 모델
└── repositories/               # 데이터 접근
```

## 아키텍처

### ADK 에이전트 구조

```
ContentHubAgent (오케스트레이터)
├── CollectorAgent (수집)
│   ├── fetch_rss        - RSS 피드 수집 (feedparser)
│   ├── fetch_youtube    - YouTube 자막 (youtube-transcript-api)
│   └── scrape_web       - 웹 스크래핑 (Playwright 4단계 폴백)
├── ProcessorAgent (처리)
│   ├── translate        - 영→한 번역
│   ├── summarize        - GeekNews 스타일 요약
│   ├── score_relevance  - AX 관련성 점수
│   └── classify         - 카테고리 분류
└── DistributorAgent (배포)
    └── send_slack_digest
```

### Cognee 메모리 통합

Cognee를 통해 ADK 에이전트에 지속적 메모리 제공:
- `add_memory`: 콘텐츠, 회사 정보, 사용자 선호도 저장
- `search_memory`: 관련 과거 콘텐츠나 컨텍스트 검색
- 멀티 워크스페이스: `get_sessionized_cognee_tools(workspace_id)`로 세션별 격리

### 스케줄러 엔드포인트

- `POST /internal/collect` - 콘텐츠 수집 (Cloud Scheduler, 1시간마다)
- `POST /internal/distribute` - 다이제스트 발송 (Cloud Scheduler, 매일 09:00)
- `/internal/*` 경로는 Cloud Run IAM + OIDC 토큰으로 보호

### 멱등성 키 규칙

- `content_key`: `{source_id}:{sha256(normalized_url)}`
  - URL 정규화: scheme/host 소문자화, 뒤 `/` 제거, 추적 파라미터 제거
- `digest_key`: `{subscription_id}:{YYYY-MM-DD}`

## Firestore 컬렉션

| 컬렉션 | 용도 |
|--------|------|
| `sources` | 콘텐츠 소스 (RSS, YouTube, 웹) |
| `contents` | 수집/처리된 콘텐츠 |
| `companies` | 회사 프로필 (맞춤화용) |
| `subscriptions` | 구독 정보 (슬랙 채널별) |
| `digests` | 발송된 다이제스트 |

## 필수 환경 변수

```bash
GCP_PROJECT_ID=               # GCP 프로젝트 ID
GOOGLE_API_KEY=               # Google AI API 키 (Gemini)
SLACK_BOT_TOKEN=              # Slack Bot OAuth 토큰
SLACK_SIGNING_SECRET=         # Slack 서명 검증 시크릿

# Cloud Tasks (프로덕션)
TASKS_MODE=direct             # direct (로컬) 또는 cloud_tasks (프로덕션)
TASKS_TARGET_URL=             # Cloud Tasks 콜백 URL
TASKS_SERVICE_ACCOUNT_EMAIL=  # 서비스 계정 이메일
```

## 코드 품질 규칙

- **Ruff**: 린팅 + 포맷팅 + import 정렬 통합 (black, isort 대체)
- **절대 임포트 강제**: 상대 임포트 금지 (`from src.models import ...`)
- **pre-commit**: 커밋 시 자동 검사 (ruff, mypy, prettier)

## 규칙

1. **한국어 응답**: 에이전트 응답은 항상 한국어
2. **GeekNews 스타일 요약**: 제목 20자 이내, 요약 3문장 이내
3. **Slack 제한 대응**: 50 blocks 초과 시 분할 발송
4. **보안**: Slack 요청은 `X-Slack-Signature` + 타임스탬프 검증

## geniefy-slack-agent 참조

이 프로젝트는 geniefy-slack-agent의 패턴을 재사용합니다:

| 대상 | 참조 파일 |
|------|----------|
| Pydantic Settings | `src/config/settings.py` |
| structlog 로깅 | `src/config/logging.py` |
| Firestore 클라이언트 | `src/adapters/firestore_client.py` |
| Slack 클라이언트 | `src/adapters/slack_client.py` |
| Cloud Tasks | `src/adapters/tasks_client.py` |
| Terraform | `infra/terraform/` |
| Bootstrap | `infra/bootstrap/` |
| ADK 에이전트 구조 | `src/agent/geniefy_agent.py` |
