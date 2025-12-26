# Implementation Plan: Phase 1 MVP - 핵심 파이프라인

**Branch**: `002-phase1-mvp-pipeline` | **Date**: 2025-12-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-phase1-mvp-pipeline/spec.md`

## Summary

RSS 피드와 YouTube 자막에서 콘텐츠를 수집하고, Gemini를 통해 한국어 번역/요약 및 AX 관련성 스코어링을 수행한 후, 슬랙 채널에 일일 다이제스트로 발송하는 핵심 파이프라인을 구현합니다.

**핵심 흐름**: 수집(Collect) → 처리(Process) → 배포(Distribute)

## Technical Context

**Language/Version**: Python 3.12+ (constitution에 명시)
**Primary Dependencies**:
- FastAPI (웹 프레임워크)
- Google ADK + Cognee (에이전트 프레임워크)
- feedparser (RSS 수집)
- youtube-transcript-api (YouTube 자막)
- google-genai (Gemini LLM - 신규 SDK)

**Storage**: Google Firestore (Phase 0에서 클라이언트 구현 완료)
**Testing**: pytest + pytest-asyncio (TDD 필수 - constitution)
**Target Platform**: Google Cloud Run (서버리스)
**Project Type**: Single backend application
**Performance Goals**:
- 콘텐츠 처리: 5분 이내/건
- 다이제스트 발송 성공률: 99%+

**Constraints**:
- Gemini API rate limit 준수
- Slack 50 blocks 제한 대응
- OIDC 토큰 인증 필수 (내부 엔드포인트)

**Scale/Scope**:
- 일일 수집 콘텐츠: 20+ 건
- 단일 워크스페이스 (Phase 1)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 원칙 | 상태 | 적용 방식 |
|------|------|----------|
| I. Test-First | ✅ 준수 | 모든 도구/서비스에 대해 테스트 먼저 작성 |
| II. API-First | ✅ 준수 | scheduler.py, internal_tasks.py 엔드포인트 스펙 먼저 정의 |
| III. Korean-First | ✅ 준수 | 다이제스트 한국어, GeekNews 스타일 |
| IV. Quality Gates | ✅ 준수 | Ruff, MyPy, pytest 통과 필수 |
| V. Simplicity | ✅ 준수 | 최소 기능 구현, 과도한 추상화 금지 |

## Project Structure

### Documentation (this feature)

```text
specs/002-phase1-mvp-pipeline/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research (if needed)
├── data-model.md        # Pydantic 모델 정의
├── quickstart.md        # 빠른 시작 가이드
├── contracts/           # API 스펙
│   └── openapi.yaml     # Internal API 정의
├── checklists/
│   └── requirements.md  # Spec 품질 체크리스트
└── tasks.md             # 구현 태스크 (/speckit.tasks 출력)
```

### Source Code (repository root)

```text
src/
├── api/
│   ├── main.py                   # FastAPI 앱 (Phase 0, 확장)
│   ├── scheduler.py              # [NEW] Cloud Scheduler 엔드포인트
│   └── internal_tasks.py         # [NEW] Cloud Tasks 콜백
│
├── agent/
│   ├── core/
│   │   ├── cognee_tools.py       # (Phase 0)
│   │   └── session_service.py    # [NEW] 세션 관리
│   ├── content_hub_agent.py      # [NEW] 메인 오케스트레이터
│   └── domains/
│       ├── collector/            # [NEW] 수집 도메인
│       │   ├── collector_agent.py
│       │   └── tools/
│       │       ├── rss_tool.py
│       │       └── youtube_tool.py
│       ├── processor/            # [NEW] 처리 도메인
│       │   ├── processor_agent.py
│       │   └── tools/
│       │       ├── translator_tool.py
│       │       ├── summarizer_tool.py
│       │       └── scorer_tool.py
│       └── distributor/          # [NEW] 배포 도메인
│           ├── distributor_agent.py
│           └── tools/
│               └── slack_sender_tool.py
│
├── models/                        # [NEW] Pydantic 도메인 모델
│   ├── source.py
│   ├── content.py
│   ├── subscription.py
│   └── digest.py
│
├── repositories/                  # [NEW] Firestore 데이터 접근
│   ├── base.py
│   ├── source_repo.py
│   ├── content_repo.py
│   ├── subscription_repo.py
│   └── digest_repo.py
│
├── services/                      # [NEW] 비즈니스 로직
│   ├── content_pipeline.py
│   ├── digest_service.py
│   └── quality_filter.py
│
├── adapters/                      # (Phase 0, 확장)
│   ├── firestore_client.py
│   ├── slack_client.py
│   ├── tasks_client.py
│   └── gemini_client.py          # [NEW] Gemini API 래퍼
│
└── config/
    ├── settings.py               # (Phase 0, 확장)
    └── logging.py

tests/
├── unit/
│   ├── adapters/                 # (Phase 0)
│   ├── agent/
│   │   ├── domains/
│   │   │   ├── collector/        # [NEW]
│   │   │   ├── processor/        # [NEW]
│   │   │   └── distributor/      # [NEW]
│   ├── models/                   # [NEW]
│   ├── repositories/             # [NEW]
│   └── services/                 # [NEW]
├── integration/                  # [NEW]
│   ├── test_collection_flow.py
│   ├── test_processing_flow.py
│   └── test_distribution_flow.py
└── conftest.py
```

**Structure Decision**: Phase 0에서 구축된 단일 백엔드 구조를 확장하여 도메인 에이전트 패턴(Collector/Processor/Distributor) 적용

## Complexity Tracking

> 현재 Constitution 위반 없음 - 추가 정당화 불필요

| 위반 | 필요성 | 거부된 단순 대안 |
|------|--------|-----------------|
| (없음) | - | - |

## Phase 0: Research Decisions

### R-001: RSS 수집 라이브러리

**Decision**: feedparser
**Rationale**: Python 표준 RSS 파싱 라이브러리, 안정성 검증됨
**Alternatives**:
- atoma: 더 현대적이나 커뮤니티 지원 부족
- 직접 XML 파싱: 불필요한 복잡성

### R-002: YouTube 자막 추출

**Decision**: youtube-transcript-api
**Rationale**: 공식 API 없이 자막 추출 가능, 무료
**Alternatives**:
- yt-dlp: 전체 영상 다운로드 필요, 오버킬
- YouTube Data API: 자막 직접 접근 불가

### R-003: LLM 호출 패턴

**Decision**: Google Gen AI SDK (google-genai)
**Rationale**: Gemini 신규 공식 SDK (google-generativeai 대체), ADK와 호환
**Alternatives**:
- LangChain: 과도한 추상화, Simplicity 원칙 위반
- 직접 REST 호출: SDK가 이미 존재함

### R-004: 멱등성 키 생성

**Decision**: `{source_id}:{sha256(normalized_url)}`
**Rationale**: URL 정규화로 추적 파라미터 제거, 해시로 길이 제한
**Normalization Rules**:
- scheme/host 소문자화
- trailing `/` 제거
- utm_*, ref, fbclid 등 추적 파라미터 제거

### R-005: 처리 상태 관리

**Decision**: Firestore 문서 필드로 상태 추적
**States**: pending → processing → completed/failed/skipped/timeout
**Rationale**: 별도 상태 저장소 불필요, 단순함 유지

## Phase 1: Design

### Data Model Summary

4개 핵심 엔티티 (상세: data-model.md)

| 엔티티 | 목적 | 주요 필드 |
|--------|------|----------|
| Source | 콘텐츠 소스 | id, type, url, is_active |
| Content | 수집/처리 결과 | content_key, processing_status, relevance_score |
| Subscription | 채널 구독 | channel_id, preferences |
| Digest | 발송 이력 | digest_key, content_ids |

### API Contracts Summary

(상세: contracts/openapi.yaml)

| 엔드포인트 | 메서드 | 인증 | 목적 |
|-----------|--------|------|------|
| `/internal/collect` | POST | OIDC | Cloud Scheduler 수집 트리거 |
| `/internal/distribute` | POST | OIDC | Cloud Scheduler 배포 트리거 |
| `/internal/tasks/process` | POST | OIDC | Cloud Tasks 처리 콜백 |
| `/api/sources` | CRUD | - | 소스 관리 (MVP 내부용) |
| `/api/subscriptions` | CRUD | - | 구독 관리 (MVP 내부용) |
| `/health` | GET | - | 헬스체크 (Phase 0) |

### Agent Architecture

```
ContentHubAgent (오케스트레이터)
    │
    ├── CollectorAgent
    │   ├── fetch_rss(source_url, source_id) → list[RawContent]
    │   └── fetch_youtube(video_id, source_id) → RawContent
    │
    ├── ProcessorAgent
    │   ├── translate(text, target_lang) → str
    │   ├── summarize(title, body) → SummaryResult
    │   └── score_relevance(title, summary) → float
    │
    └── DistributorAgent
        └── send_slack_digest(subscription, contents) → bool
```

### LLM Prompts

**요약 프롬프트** (GeekNews 스타일):
```
다음 글을 GeekNews 스타일로 요약해주세요.

규칙:
1. 제목: 핵심 가치가 드러나는 한 줄 (20자 이내)
2. 요약: 3문장 이내로 핵심만
3. 왜 중요한지: 1문장으로 임팩트 설명

JSON 형식으로 응답:
{"title_ko": "...", "summary_ko": "...", "why_important": "..."}

원문:
제목: {title}
본문: {body}
```

**스코어링 프롬프트**:
```
다음 콘텐츠가 AI Transformation(AX)과 얼마나 관련 있는지 평가해주세요.

AX 관련 주제:
- AI/ML 기술 발전
- 기업 AI 도입 사례
- AI 도구 및 서비스
- AI 윤리 및 규제
- 자동화 및 생산성

0.0~1.0 사이 점수로만 응답 (예: 0.85)

제목: {title}
요약: {summary}
```

### Slack Message Format

```
🔥 오늘의 AX 다이제스트 ({count}건)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ {title_ko}
→ {summary_ko}
💡 {why_important}
🔗 <{original_url}|원문 보기>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[다음 콘텐츠들...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 {date} | 🤖 AX Content Hub
```

## Implementation Phases

### Phase A: 기반 구조 (models, repositories)

1. Pydantic 모델 정의 (Source, Content, Subscription, Digest)
2. Repository 베이스 클래스 및 구현체
3. Gemini 클라이언트 어댑터
4. Settings 확장 (새 환경변수)

### Phase B: 수집 에이전트 (collector)

1. RSS 수집 도구 (feedparser)
2. YouTube 자막 도구 (youtube-transcript-api)
3. CollectorAgent 구현
4. 중복 방지 로직 (content_key)

### Phase C: 처리 에이전트 (processor)

1. 번역 도구 (Gemini)
2. 요약 도구 (Gemini, GeekNews 스타일)
3. 스코어링 도구 (Gemini)
4. ProcessorAgent 구현
5. JSON 파싱 재시도 로직

### Phase D: 배포 에이전트 (distributor)

1. Slack 다이제스트 빌더 (Block Kit)
2. 분할 발송 로직 (50 blocks 제한)
3. DistributorAgent 구현
4. 중복 발송 방지 (digest_key)

### Phase E: 파이프라인 통합

1. ContentHubAgent 오케스트레이터
2. 스케줄러 엔드포인트 (/internal/collect, /internal/distribute)
3. Cloud Tasks 콜백 (/internal/tasks/process)
4. 품질 필터링 서비스

### Phase F: 테스트 및 검증

1. 통합 테스트 (수집→처리→배포 플로우)
2. Edge case 테스트
3. E2E 테스트 (실제 피드로 검증)

## Dependencies on Phase 0

| Phase 0 컴포넌트 | Phase 1 사용처 |
|------------------|----------------|
| FirestoreClient | Repository 구현 |
| SlackClient | DistributorAgent |
| TasksClient | 비동기 처리 큐잉 |
| Settings | 새 환경변수 추가 |
| structlog | 전체 로깅 |

## Risk Mitigation

| 리스크 | 대응 |
|--------|------|
| Gemini API 지연 | 30초 타임아웃, 재시도 로직 |
| 잘못된 JSON 응답 | 3회 재시도, 원본 유지 폴백 |
| Slack rate limit | 지수 백오프 (최대 5회) |
| YouTube 자막 없음 | skipped 상태로 기록, Phase 2 STT 대상 |

## Next Steps

1. `/speckit.tasks` 실행하여 구현 태스크 분해
2. Phase A부터 TDD로 구현 시작
3. 각 Phase 완료 시 통합 테스트 실행
