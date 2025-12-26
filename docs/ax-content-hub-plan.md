# AX Content Hub - 개발 계획서

> AX(AI Transformation) 콘텐츠를 큐레이션하여 슬랙으로 전달하는 봇

## 설계 결정 사항

| 항목 | 결정 | 근거 |
|------|------|------|
| 패키지 매니저 | uv | 빠른 의존성 설치, geniefy에서 검증 |
| LLM 모델 | gemini-3-flash-preview | 최신 모델, geniefy에서 검증 |
| Google ADK | 전체 파이프라인에 활용 | 수집/처리/배포를 도메인 에이전트로 분리 |
| AI 메모리 | Cognee | ADK 네이티브 통합, 지식 그래프 + 벡터 검색, 세션 격리 |
| 벡터 DB | Firestore만 사용 | Pinecone 제외, 비용/복잡도 절감 |
| 슬랙 기능 | 다이제스트 발송만 (MVP) | 슬래시 커맨드/대화 기능은 Phase 2 이후 |
| 내부 트리거 인증 | Cloud Run IAM + Scheduler OIDC 토큰 | 공개 호출 차단 |
| 슬랙 배포 (MVP) | 단일 워크스페이스, OAuth 미사용 | 초기 운영 단순화 |

---

## 1. 프로젝트 개요

### 1.1 비전

- **목표**: AX 관련 해외 콘텐츠를 큐레이션하여 한국 기업에 슬랙으로 전달
- **핵심 가치**: "읽어야 할 것"이 아니라 "이미 정리된 것"을 받는 경험
- **차별화**: 회사 상황에 맞는 맞춤형 인사이트 제공

### 1.2 핵심 기능

| 구분 | 기능 | 우선순위 |
|------|------|----------|
| **수집** | RSS 피드 구독 | P0 |
| | YouTube 영상 → 텍스트 (기존 자막) | P0 |
| | 웹 스크래핑 (RSS 없는 사이트) | P1 |
| | YouTube STT 폴백 (자막 없는 경우) | P1 |
| | 뉴스레터 파싱 | P2 |
| **처리** | 다국어 번역 (영→한) | P0 |
| | GeekNews 스타일 요약 | P0 |
| | AX 관련성 스코어링 | P0 |
| | 카테고리 자동 분류 | P1 |
| | 회사 맞춤 인사이트 | P1 |
| **배포** | 슬랙봇 (단일 워크스페이스) | P0 |
| | 슬랙봇 (멀티 워크스페이스) | P1 |
| | 뉴스레터 발송 | P2 |
| | 팀즈/카카오톡 확장 | P3 |
| **운영** | 분석 API | P1 |
| | AX 담당자 연결 (리드) | P2 |

---

## 2. 기술 스택

```
┌─────────────────────────────────────────────────────────────┐
│                        Backend                               │
│  Python 3.12 + FastAPI + Google ADK + Cognee + Cloud Run    │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                        AI Memory Layer                       │
│  Cognee (지식 그래프 + 벡터 검색, 세션별 메모리 격리)          │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                        Data Layer                            │
│  Firestore (메인 DB) + BigQuery (분석, 선택)                 │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                        Infrastructure                        │
│  GCP (Cloud Run, Cloud Scheduler, Cloud Tasks, Secret Mgr)  │
│  Terraform + GitHub Actions CI/CD                           │
└─────────────────────────────────────────────────────────────┘
```

### 기술 선정 근거

| 선택 | 근거 |
|------|------|
| Python + FastAPI | geniefy에서 검증된 스택, LLM 생태계 최적 |
| Google ADK | 멀티 에이전트 오케스트레이션 (geniefy 패턴 재사용) |
| Cognee | ADK 네이티브 통합, ECL 파이프라인(Collect→Process→Distribute), 세션별 메모리 격리 |
| Firestore | 스키마리스, 실시간 업데이트, 비용 효율 |
| Cloud Run | 서버리스, 자동 스케일링, 비용 효율 |
| Cloud Tasks | 비동기 처리, 재시도 로직 (geniefy 패턴) |

---

## 3. 시스템 아키텍처

```
                                    ┌─────────────────┐
                                    │  Cloud Scheduler │
                                    │   (1시간마다)     │
                                    └────────┬────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Content Collector Service                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │RSS Reader│ │Playwright│ │YouTube   │ │Gmail API │           │
│  │          │ │Scraper   │ │Transcript│ │Parser    │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────┬───────────────────────────────────┘
                              │ Raw Content
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Content Processor Service                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Translator│ │Summarizer│ │ Scorer   │ │Classifier│           │
│  │(Gemini)  │ │(Gemini)  │ │(Gemini)  │ │(Gemini)  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                              │                                   │
│                    ┌─────────┴─────────┐                        │
│                    │ Insight Generator │ ← Company Profile       │
│                    │    (Gemini)       │                        │
│                    └───────────────────┘                        │
└─────────────────────────────┬───────────────────────────────────┘
                              │ Processed Content
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Firestore                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ contents │ │ sources  │ │companies │ │  subs    │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
                      ┌───────────────┐
                      │   Slack Bot   │
                      │   (FastAPI)   │
                      └───────────────┘
```

---

## 4. 데이터 모델

### 4.1 sources - 콘텐츠 소스 관리

```python
{
    "id": "src_001",
    "name": "OpenAI Blog",
    "type": "rss",  # rss | web | youtube | newsletter
    "url": "https://openai.com/blog/rss",
    "config": {
        "selector": ".post-item",  # web 타입용
        "fallback_strategy": "structural",
    },
    "category": "AI_RESEARCH",
    "language": "en",
    "is_active": True,
    "last_fetched_at": "2024-01-15T09:00:00Z",
}
```

### 4.2 contents - 수집된 콘텐츠

```python
{
    "id": "cnt_abc123",
    "source_id": "src_001",
    "original_url": "https://openai.com/blog/...",
    "content_key": "src_001:sha256(original_url)",  # 멱등성/중복 방지 키
    "original_title": "Introducing GPT-5",
    "original_language": "en",

    # 처리 결과
    "title_ko": "GPT-5 공개: 추론 능력 대폭 향상",
    "summary_ko": "OpenAI가 새로운 모델 GPT-5를 공개했습니다...",
    "why_important": "기업 AI 도입 전략에 직접적 영향",

    # 메타데이터
    "categories": ["AI_MODEL", "REASONING"],
    "relevance_score": 0.95,
    "quality_score": 0.88,

    # 처리 상태 (파이프라인 추적용)
    "processing_status": "completed",  # pending | processing | completed | failed
    "processing_attempts": 1,
    "last_error": None,

    # 발행 상태
    "status": "published",  # draft | review | published | archived
    "collected_at": "2024-01-15T08:00:00Z",
    "processed_at": "2024-01-15T08:05:00Z",
    "published_at": "2024-01-15T10:00:00Z",

    # 인터랙션
    "stats": {
        "views": 150,
        "clicks": 45,
        "reactions": {"🔥": 12, "👍": 28, "🤔": 3},
        "shares": 5,
    },
}
```

### 4.3 companies - 회사 프로필 (맞춤화용)

```python
{
    "id": "comp_xyz",
    "name": "ABC Corporation",
    "industry": "금융",
    "size": "대기업",
    "ai_maturity": "초기",  # 초기 | 도입중 | 성숙
    "interests": ["챗봇", "문서자동화", "리스크분석"],
    "pain_points": ["레거시 시스템 연동", "규제 준수"],
    "custom_prompt": "금융권 규제 관점에서 분석해줘",
}
```

### 4.4 subscriptions - 구독 정보

```python
{
    "id": "sub_001",
    "platform": "slack",  # slack | teams | kakao | email
    "platform_config": {
        "team_id": "T12345",
        "channel_id": "C12345",
        "webhook_secret_id": "slack/webhook/sub_001",  # Secret Manager 참조
    },
    "company_id": "comp_xyz",  # nullable

    # 구독 설정
    "preferences": {
        "frequency": "daily",  # realtime | daily | weekly
        "delivery_time": "09:00",
        "categories": ["AI_STRATEGY", "CASE_STUDY"],
        "min_relevance": 0.7,
        "language": "ko",
    },

    "is_active": True,
    "created_at": "2024-01-01T00:00:00Z",
}
```

### 4.5 digests - 발송된 다이제스트

```python
{
    "id": "dig_001",
    "subscription_id": "sub_001",
    "digest_key": "sub_001:2024-01-15",  # 구독+날짜 기준 멱등성 키
    "content_ids": ["cnt_abc123", "cnt_def456"],
    "sent_at": "2024-01-15T09:00:00Z",
    "opened_at": "2024-01-15T09:15:00Z",
    "clicks": [
        {"content_id": "cnt_abc123", "clicked_at": "..."},
    ],
}
```

### 4.6 멱등성 키 규칙

- `content_key`: `{source_id}:{sha256(normalized_url)}`
  - `normalized_url`: scheme/host 소문자화, 뒤 `/` 제거, 추적 파라미터(`utm_*`, `ref`, `fbclid`) 제거
- `digest_key`: `{subscription_id}:{YYYY-MM-DD}` (Cloud Scheduler 설정 시간대 기준)

---

## 5. 개발 단계

### Phase 0: 프로젝트 초기화 (geniefy 재사용 + Cognee 통합)

**목표**: 개발 환경 및 인프라 기반 구축, Cognee 통합

#### 0-1. geniefy 재사용

| 작업 | 참고 소스 (geniefy-slack-agent) |
|------|-------------------------------|
| pyproject.toml 설정 (uv) | `pyproject.toml` |
| Pydantic Settings | `src/config/settings.py` |
| structlog 로깅 | `src/config/logging.py` |
| Firestore 클라이언트 | `src/adapters/firestore_client.py` |
| Slack 클라이언트 | `src/adapters/slack_client.py` |
| Cloud Tasks 클라이언트 | `src/adapters/tasks_client.py` |
| Terraform 모듈 | `infra/terraform/` |
| Bootstrap 스크립트 | `infra/bootstrap/` |
| Dockerfile | `Dockerfile` |

#### 0-2. Cognee 통합 (ADK 지속적 메모리)

**Cognee란?**
- AI 에이전트에 지속적인 메모리 계층 제공
- ECL 파이프라인: Extract → Cognify → Load (수집 → 처리 → 배포와 유사)
- 지식 그래프 + 벡터 검색 결합
- 세션별 메모리 격리 (멀티 워크스페이스 지원)

**설치**:
```bash
uv add cognee cognee-integration-google-adk
```

**ADK 에이전트에 Cognee 메모리 도구 통합**:

```python
# src/agent/core/cognee_tools.py
from cognee_integration_google_adk import add_tool, search_tool, get_sessionized_cognee_tools

def get_cognee_tools(session_id: str | None = None):
    """Cognee 메모리 도구 반환

    Args:
        session_id: 세션 ID (멀티 워크스페이스용, 예: workspace_id)

    Returns:
        (add_tool, search_tool) 튜플
    """
    if session_id:
        # 멀티 워크스페이스: 세션별 격리된 메모리
        return get_sessionized_cognee_tools(session_id)
    else:
        # 단일 워크스페이스: 공유 메모리
        return add_tool, search_tool
```

**에이전트에서 사용**:

```python
# src/agent/content_hub_agent.py
from google.adk.agents import Agent
from src.agent.core.cognee_tools import get_cognee_tools

def create_content_hub_agent(workspace_id: str = None) -> Agent:
    """콘텐츠 허브 메인 에이전트 (Cognee 메모리 포함)"""

    add_memory, search_memory = get_cognee_tools(workspace_id)

    return Agent(
        name="content_hub_agent",
        model="gemini-3-flash-preview",
        instruction="""
        당신은 AX 콘텐츠 큐레이터입니다.

        메모리 활용:
        - add_memory: 중요한 콘텐츠, 회사 정보, 사용자 선호도를 저장
        - search_memory: 관련 과거 콘텐츠나 컨텍스트를 검색

        수집된 콘텐츠는 메모리에 저장하여 향후 관련성 분석에 활용합니다.
        """,
        tools=[
            add_memory,      # 정보 저장
            search_memory,   # 지식 검색
            # ... 기타 도구
        ],
    )
```

**Cognee 활용 시나리오**:

| 시나리오 | add_memory | search_memory |
|---------|-----------|---------------|
| 콘텐츠 수집 | 새 콘텐츠 메타데이터 저장 | 중복 콘텐츠 검색 |
| 맞춤 인사이트 | 회사 프로필 저장 | 회사 관련 과거 콘텐츠 검색 |
| 다이제스트 생성 | 발송 이력 저장 | 최근 발송 내용 검색 (중복 방지) |
| 피드백 반영 | 사용자 반응 저장 | 선호도 패턴 검색 |

---

### Phase 1: MVP - 핵심 파이프라인

**목표**: RSS + YouTube 수집 → LLM 요약 → 슬랙 전송의 기본 루프 완성

#### 1-1. 프로젝트 구조 (ADK 에이전트 중심)

```
ax-content-hub/
├── src/
│   ├── api/                        # FastAPI 앱
│   │   ├── main.py                 # 라이프사이클 관리
│   │   ├── scheduler.py            # Cloud Scheduler 엔드포인트
│   │   └── internal_tasks.py       # Cloud Tasks 콜백
│   │
│   ├── agent/                      # Google ADK 에이전트
│   │   ├── content_hub_agent.py    # 메인 에이전트 (오케스트레이터)
│   │   ├── core/
│   │   │   ├── session_service.py
│   │   │   └── cognee_tools.py     # Cognee 메모리 도구
│   │   └── domains/
│   │       ├── collector/          # 수집 에이전트
│   │       │   ├── collector_agent.py
│   │       │   └── tools/
│   │       │       ├── rss_tool.py
│   │       │       ├── web_scraper_tool.py
│   │       │       └── youtube_tool.py
│   │       ├── processor/          # 처리 에이전트
│   │       │   ├── processor_agent.py
│   │       │   └── tools/
│   │       │       ├── translator_tool.py
│   │       │       ├── summarizer_tool.py
│   │       │       └── scorer_tool.py
│   │       └── distributor/        # 배포 에이전트
│   │           ├── distributor_agent.py
│   │           └── tools/
│   │               └── slack_sender_tool.py
│   │
│   ├── services/                   # 비즈니스 로직
│   │   ├── content_pipeline.py
│   │   ├── digest_service.py
│   │   └── quality_filter.py
│   │
│   ├── models/                     # Pydantic 모델
│   │   ├── source.py
│   │   ├── content.py
│   │   ├── company.py
│   │   ├── subscription.py
│   │   └── digest.py
│   │
│   ├── adapters/                   # 외부 서비스 클라이언트
│   │   ├── firestore_client.py
│   │   ├── gemini_client.py
│   │   ├── slack_client.py
│   │   ├── tasks_client.py
│   │   └── embedding_client.py
│   │
│   ├── repositories/               # 데이터 접근
│   │   ├── source_repo.py
│   │   ├── content_repo.py
│   │   ├── company_repo.py
│   │   └── subscription_repo.py
│   │
│   └── config/
│       ├── settings.py             # Pydantic Settings
│       └── logging.py              # structlog
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── infra/
│   ├── bootstrap/
│   │   ├── bootstrap.sh
│   │   └── create-secrets.sh
│   └── terraform/
│       ├── main.tf
│       ├── variables.tf
│       └── modules/
│
├── pyproject.toml
├── Dockerfile
└── README.md
```

#### 1-2. Google ADK 에이전트 구조

```python
# src/agent/content_hub_agent.py
from google.adk.agents import Agent
from src.agent.core.cognee_tools import get_cognee_tools

class ContentHubAgent:
    """콘텐츠 허브 메인 에이전트

    역할:
    - 오케스트레이션: 수집/처리/배포 에이전트 조율
    - 파이프라인 관리: 콘텐츠 흐름 제어
    - 지식 관리: Cognee를 통한 지속적 메모리 활용
    """

    def __init__(self, workspace_id: str = None):
        self.workspace_id = workspace_id
        self.add_memory, self.search_memory = get_cognee_tools(workspace_id)

        self.collector = CollectorAgent()
        self.processor = ProcessorAgent()
        self.distributor = DistributorAgent()

    async def run_collection_pipeline(self, sources: list[Source]):
        """수집 파이프라인 실행 - 새 콘텐츠를 메모리에 저장"""

    async def run_processing_pipeline(self, contents: list[Content]):
        """처리 파이프라인 실행 - 메모리에서 관련 컨텍스트 검색"""

    async def run_distribution_pipeline(self, subscription: Subscription):
        """배포 파이프라인 실행 - 발송 이력을 메모리에 저장"""
```

```python
# src/agent/domains/collector/collector_agent.py
def create_collector_agent() -> Agent:
    """콘텐츠 수집 에이전트

    도구:
    - fetch_rss: RSS 피드 수집 (P0)
    - fetch_youtube: YouTube 자막 수집 (P0)
    - scrape_web: 웹 페이지 스크래핑 (P1)
    """
    return Agent(
        name="collector_agent",
        model="gemini-3-flash-preview",
        instruction="콘텐츠 소스에서 새로운 콘텐츠를 수집합니다.",
        tools=[fetch_rss, fetch_youtube, scrape_web],
    )
```

```python
# src/agent/domains/processor/processor_agent.py
def create_processor_agent() -> Agent:
    """콘텐츠 처리 에이전트

    도구:
    - translate: 영→한 번역
    - summarize: GeekNews 스타일 요약
    - score_relevance: AX 관련성 점수
    - classify: 카테고리 분류
    """
    return Agent(
        name="processor_agent",
        model="gemini-3-flash-preview",
        instruction="수집된 콘텐츠를 번역, 요약, 스코어링합니다.",
        tools=[translate, summarize, score_relevance, classify],
    )
```

```python
# src/agent/domains/distributor/distributor_agent.py
def create_distributor_agent() -> Agent:
    """콘텐츠 배포 에이전트

    도구:
    - send_slack_digest: 슬랙 다이제스트 발송
    """
    return Agent(
        name="distributor_agent",
        model="gemini-3-flash-preview",
        instruction="처리된 콘텐츠를 슬랙으로 발송합니다.",
        tools=[send_slack_digest],
    )
```

#### 1-3. RSS 수집 도구

```python
# src/agent/domains/collector/tools/rss_tool.py
@tool
async def fetch_rss(source_url: str, source_id: str) -> list[dict]:
    """RSS 피드에서 새 콘텐츠 수집

    Args:
        source_url: RSS 피드 URL
        source_id: 소스 ID

    Returns:
        수집된 콘텐츠 목록
    """
    feed = feedparser.parse(source_url)

    new_contents = []
    for entry in feed.entries:
        if await is_already_collected(entry.link):
            continue

        content = {
            "source_id": source_id,
            "url": entry.link,
            "title": entry.title,
            "body": extract_body(entry),
            "published_at": parse_date(entry),
        }
        new_contents.append(content)

    return new_contents
```

#### 1-4. YouTube 자막 수집 도구

```python
# src/agent/domains/collector/tools/youtube_tool.py
from youtube_transcript_api import YouTubeTranscriptApi

@tool
async def fetch_youtube(video_id: str, source_id: str) -> dict:
    """YouTube 영상에서 자막 추출 (기존 자막 활용)

    Args:
        video_id: YouTube 영상 ID
        source_id: 소스 ID

    Returns:
        수집된 콘텐츠
    """
    # youtube-transcript-api로 기존 자막 가져오기 (비용 無)
    transcript = YouTubeTranscriptApi.get_transcript(
        video_id, languages=["en", "ko"]
    )
    body = " ".join([t["text"] for t in transcript])

    return {
        "source_id": source_id,
        "url": f"https://youtube.com/watch?v={video_id}",
        "title": await get_video_title(video_id),
        "body": body,
    }
```

#### 1-5. LLM 처리 도구

```python
# src/agent/domains/processor/tools/summarizer_tool.py
@tool
async def summarize(title: str, body: str) -> dict:
    """GeekNews 스타일로 콘텐츠 요약

    Args:
        title: 원문 제목
        body: 원문 본문 (번역된 텍스트)

    Returns:
        {"title_ko": "...", "summary_ko": "...", "why_important": "..."}
    """
    # Gemini를 통해 요약 생성
    raw = await llm.generate(prompt)
    result = parse_json_or_retry(raw)  # JSON 파싱 실패 시 재시도/폴백
    return result
```

**요약 프롬프트**:

```
다음 글을 GeekNews 스타일로 요약해주세요.

규칙:
1. 제목: 핵심 가치가 드러나는 한 줄 (20자 이내)
2. 요약: 3문장 이내로 핵심만
3. 왜 중요한지: 1문장으로 임팩트 설명

JSON 형식으로 응답:
{"title": "...", "body": "...", "why_important": "..."}
```

#### 1-4. 슬랙봇 기본 기능

```python
class SlackDistributor:
    """슬랙 배포 채널"""

    async def send_digest(
        self,
        subscription: Subscription,
        contents: list[ProcessedContent]
    ) -> None:
        blocks = self._build_digest_blocks(contents)
        blocks = self._truncate_or_split_blocks(blocks)  # Slack 50 blocks 제한 대응

        await self.slack_client.chat_postMessage(
            channel=subscription.platform_config["channel_id"],
            blocks=blocks,
            text=f"🔥 오늘의 AX 다이제스트 ({len(contents)}건)",
        )
```

**슬랙 메시지 예시**:

```
🔥 오늘의 AX 다이제스트 (3건)

1. OpenAI, 새로운 추론 모델 공개
   → 복잡한 작업에서 GPT-4 대비 3배 성능
   🔗 원문 | 👍 12 | 🔥 5

2. 맥킨지 "AI 도입 기업 40%가 실패하는 이유"
   → 기술보다 조직문화가 핵심
   🔗 원문 | 👍 8

💡 ABC Corp 맞춤 인사이트:
   금융권 챗봇 도입 사례가 2건 있어요. 관심 있으시면 알려드릴게요!
```

#### 1-5. 스케줄러 연동

```python
# /internal/*는 Cloud Run IAM으로 보호, Scheduler는 OIDC 토큰 사용
@app.post("/internal/collect")
async def trigger_collection():
    """Cloud Scheduler에서 호출 - 콘텐츠 수집 트리거 (OIDC 인증)"""
    sources = await source_repo.get_active_sources()

    for source in sources:
        collector = collectors.get(source.type)
        raw_contents = await collector.collect(source)

        for raw in raw_contents:
            # content_key = hash(source_id + url)
            if await content_repo.exists(raw.content_key):
                continue  # 중복 수집 방지
            await task_queue.enqueue(
                "process_content",
                raw.model_dump(),
                task_id=raw.content_key,
            )

    return {"status": "ok", "sources_processed": len(sources)}


@app.post("/internal/distribute")
async def trigger_distribution():
    """Cloud Scheduler에서 호출 - 다이제스트 발송 (OIDC 인증)"""
    subscriptions = await subscription_repo.get_due_subscriptions()

    for sub in subscriptions:
        digest_key = f"{sub.id}:{today()}"
        if await digest_repo.exists(digest_key):
            continue  # 중복 발송 방지
        contents = await content_repo.get_contents_for_subscription(sub)
        if contents:
            distributor = get_distributor(sub.platform)
            await distributor.send_digest(sub, contents)
            await digest_repo.save(Digest(
                subscription_id=sub.id,
                digest_key=digest_key,
                content_ids=[c.id for c in contents],
            ))

    return {"status": "ok", "subscriptions_processed": len(subscriptions)}
```

#### 1-6. MVP 인프라 (Terraform)

```hcl
# Cloud Run - API 서버
resource "google_cloud_run_service" "api" {
  name     = "ax-content-hub-api"
  location = "asia-northeast3"

  template {
    spec {
      containers {
        image = var.api_image
      }
    }
  }
}

# Cloud Scheduler - 수집 트리거 (1시간마다)
resource "google_cloud_scheduler_job" "collect" {
  name     = "trigger-collection"
  schedule = "0 * * * *"

  http_target {
    uri         = "${google_cloud_run_service.api.status[0].url}/internal/collect"
    http_method = "POST"
    oidc_token {
      service_account_email = var.scheduler_sa_email
      audience              = google_cloud_run_service.api.status[0].url
    }
  }
}

# Cloud Scheduler - 배포 트리거 (매일 9시)
resource "google_cloud_scheduler_job" "distribute" {
  name     = "trigger-distribution"
  schedule = "0 9 * * *"

  http_target {
    uri         = "${google_cloud_run_service.api.status[0].url}/internal/distribute"
    http_method = "POST"
    oidc_token {
      service_account_email = var.scheduler_sa_email
      audience              = google_cloud_run_service.api.status[0].url
    }
  }
}
```

**보안 설정**:
- Cloud Run은 인증 필요로 설정
- Scheduler 서비스 계정에만 `roles/run.invoker` 부여

#### 1-7. MVP 최소 보안 체크리스트

- Cloud Run은 인증 필요, Scheduler OIDC 토큰만 허용
- Scheduler OIDC `audience`는 Cloud Run URL로 설정
- Slack 요청은 `X-Slack-Signature` + 타임스탬프(예: 5분 이내) 검증
- Slack Webhook/토큰은 Secret Manager에 보관하고 로그에 남기지 않음

---

### Phase 2: 콘텐츠 수집 확장

**목표**: RSS 외 다양한 소스 지원

#### 2-1. 웹 스크래핑 (Playwright 4단계 폴백)

```python
class WebCollector:
    """Playwright 기반 웹 스크래핑 (4단계 폴백)"""

    async def _extract_with_fallback(self, page, config: dict) -> list[dict]:
        # 1단계: Static + Selector (가장 빠름)
        if selector := config.get("selector"):
            try:
                items = await self._extract_by_selector(page, selector)
                if items:
                    return items
            except Exception:
                pass

        # 2단계: Dynamic + Selector (JS 렌더링 대기)
        try:
            await page.wait_for_load_state("networkidle")
            items = await self._extract_by_selector(page, selector)
            if items:
                return items
        except Exception:
            pass

        # 3단계: Structural (위치 기반)
        try:
            items = await self._extract_by_structure(page)
            if items:
                return items
        except Exception:
            pass

        # 4단계: URL-based (링크 패턴 분석)
        return await self._extract_by_url_pattern(page, config.get("url_pattern"))
```

#### 2-2. YouTube STT 폴백 (자막 없는 경우)

Phase 1에서 youtube-transcript-api로 기존 자막을 가져오지 못한 경우의 폴백 처리.

**활용 라이브러리**:
- [yt_dlp_transcript](https://github.com/kkensuke/yt_dlp_transcript) - yt-dlp + Whisper + Gemini 요약

```python
# src/agent/domains/collector/tools/youtube_tool.py (확장)
async def fetch_youtube_with_fallback(video_id: str, source_id: str) -> dict:
    """YouTube 자막 수집 - STT 폴백 포함"""

    # 1단계: 기존 자막 시도 (Phase 1에서 구현)
    try:
        return await fetch_youtube(video_id, source_id)
    except TranscriptsDisabled:
        pass  # 자막 없음, 2단계로

    # 2단계: yt_dlp_transcript 활용 (yt-dlp + Whisper)
    # yt_dlp_transcript 라이브러리 활용
    transcript = await transcribe_with_yt_dlp_transcript(video_id)
    return {
        "source_id": source_id,
        "url": f"https://youtube.com/watch?v={video_id}",
        "title": await get_video_title(video_id),
        "body": transcript,
    }
```

#### 2-3. 품질 필터링

```python
class QualityFilter:
    """콘텐츠 품질 필터링"""

    async def filter(self, content: ProcessedContent) -> FilterResult:
        checks = await asyncio.gather(
            self._check_duplicate(content),    # 유사 콘텐츠 중복 체크
            self._check_relevance(content),    # AX 관련성 체크
            self._check_recency(content),      # 최신성 체크
            self._check_quality(content),      # 품질 체크
        )

        reasons = [c for c in checks if c is not None]
        return FilterResult(passed=len(reasons) == 0, reasons=reasons)
```

---

### Phase 3: 멀티 워크스페이스 및 맞춤화

**목표**: 여러 슬랙 워크스페이스 지원 + 회사별 맞춤 인사이트

#### 3-1. 멀티 워크스페이스 슬랙 앱 (OAuth 2.0)

```python
@app.get("/slack/install")
async def slack_install():
    """Slack 앱 설치 시작"""
    state = create_oauth_state()  # CSRF 방지 (서버에 저장)
    return RedirectResponse(
        f"https://slack.com/oauth/v2/authorize?"
        f"client_id={settings.SLACK_CLIENT_ID}&"
        f"scope=chat:write,commands,app_mentions:read&"
        f"redirect_uri={settings.SLACK_REDIRECT_URI}&"
        f"state={state}"
    )


@app.get("/slack/callback")
async def slack_callback(code: str, state: str):
    """OAuth 콜백 - 워크스페이스 등록"""
    if not verify_oauth_state(state):
        raise HTTPException(status_code=400, detail="invalid_state")
    response = await httpx.post(
        "https://slack.com/api/oauth.v2.access",
        data={
            "client_id": settings.SLACK_CLIENT_ID,
            "client_secret": settings.SLACK_CLIENT_SECRET,
            "code": code,
        }
    )
    data = response.json()

    # 워크스페이스 정보 저장
    await workspace_repo.save(Workspace(
        team_id=data["team"]["id"],
        team_name=data["team"]["name"],
        access_token=encrypt(data["access_token"]),
        bot_user_id=data["bot_user_id"],
    ))

    return RedirectResponse("/slack/success")
```

#### 3-2. 회사 프로필 관리

```python
@app.post("/companies")
async def create_company(data: CompanyCreate, user: User = Depends(get_current_user)):
    """회사 프로필 생성"""
    company = Company(
        id=generate_id(),
        name=data.name,
        industry=data.industry,
        size=data.size,
        ai_maturity=data.ai_maturity,
        interests=data.interests,
        pain_points=data.pain_points,
        custom_prompt=data.custom_prompt,
        owner_id=user.id,
    )
    await company_repo.save(company)
    return company
```

#### 3-3. 맞춤 인사이트 생성

```python
class InsightGenerator:
    """회사 맞춤 인사이트 생성"""

    async def generate(
        self,
        content: ProcessedContent,
        company: Company
    ) -> str:
        prompt = f"""
        다음 콘텐츠를 {company.name}의 관점에서 분석해주세요.

        [회사 정보]
        - 산업: {company.industry}
        - 규모: {company.size}
        - AI 도입 단계: {company.ai_maturity}
        - 관심 분야: {", ".join(company.interests)}
        - 고민/과제: {", ".join(company.pain_points)}

        [사용자 지정 요청]
        {company.custom_prompt or "없음"}

        [콘텐츠]
        제목: {content.title_ko}
        요약: {content.summary_ko}

        2-3문장으로 이 회사에 어떻게 적용할 수 있을지 인사이트를 제공해주세요.
        """

        return await self.llm.generate(prompt)
```

#### 3-4. 슬랙 슬래시 커맨드

```python
@app.post("/slack/commands")
async def handle_slash_command(
    payload: SlackCommandPayload,
    request: Request,
):
    """슬래시 커맨드 처리"""
    verify_slack_signature(request)  # X-Slack-Signature/Request-Timestamp 검증

    if payload.command == "/ax-setup":
        # 회사 프로필 설정 모달 열기
        await open_setup_modal(payload.trigger_id)

    elif payload.command == "/ax-digest":
        # 즉시 다이제스트 요청
        await send_instant_digest(payload.channel_id)

    elif payload.command == "/ax-search":
        # 콘텐츠 검색
        results = await search_contents(payload.text)
        await send_search_results(payload.channel_id, results)
```

---

### Phase 4: 운영 및 성장

**목표**: 분석, 리드 수집, 비용 최적화

#### 4-1. 분석 API

```python
@app.get("/analytics/overview")
async def get_overview():
    return {
        "total_contents": await content_repo.count(),
        "total_subscriptions": await subscription_repo.count(),
        "total_workspaces": await workspace_repo.count(),
        "popular_categories": await analytics.get_popular_categories(),
        "top_contents": await analytics.get_top_contents(days=7),
    }
```

#### 4-2. 리드 수집 (AX 담당자 연결)

```python
@app.post("/slack/actions")
async def handle_slack_action(payload: dict, request: Request):
    verify_slack_signature(request)  # X-Slack-Signature/Request-Timestamp 검증
    action = payload["actions"][0]

    if action["action_id"] == "request_consultation":
        lead = Lead(
            source="slack_digest",
            workspace_id=payload["team"]["id"],
            user_id=payload["user"]["id"],
        )
        await lead_repo.save(lead)
        await notify_sales_team(lead)

        return {"text": "상담 신청이 완료되었습니다!"}
```

#### 4-3. 비용 최적화

```python
class CostOptimizer:
    async def should_process(self, raw: RawContent) -> bool:
        # 1. 제목 기반 빠른 필터링 (Gemini Flash - 저비용)
        is_relevant = await self.quick_relevance_check(raw.title)
        if not is_relevant:
            return False

        # 2. 중복 체크 (임베딩 비용만)
        is_duplicate = await self.check_duplicate(raw.url)
        if is_duplicate:
            return False

        return True
```

---

### Phase 5: 배포 채널 확장 (선택)

**목표**: 슬랙 외 채널 지원 (필요시)

#### 5-1. 뉴스레터 (Resend)

```python
class EmailDistributor:
    async def send_newsletter(
        self,
        subscribers: list[str],
        contents: list[ProcessedContent]
    ):
        html = self._render_newsletter(contents)

        await self.resend.emails.send({
            "from": "AX Hub <digest@axhub.io>",
            "to": subscribers,
            "subject": f"🔥 이번 주 AX 트렌드 Top {len(contents)}",
            "html": html,
        })
```

#### 5-2. 팀즈/카카오톡 (선택적 확장)

- MS Teams: Incoming Webhook 또는 Bot Framework
- 카카오톡: 카카오 i 오픈빌더 또는 카카오워크 API

---

## 6. geniefy-slack-agent 참고 자료

### 직접 복사/수정 가능한 파일

| 대상 | geniefy 파일 |
|------|-------------|
| 설정 관리 | `src/config/settings.py` |
| 로깅 | `src/config/logging.py` |
| Firestore 클라이언트 | `src/adapters/firestore_client.py` |
| Slack 클라이언트 | `src/adapters/slack_client.py` |
| Cloud Tasks | `src/adapters/tasks_client.py` |
| Embedding 클라이언트 | `src/adapters/embedding_client.py` |
| Terraform | `infra/terraform/` |
| Bootstrap | `infra/bootstrap/` |
| Dockerfile | `Dockerfile` |

### 패턴 참고

| 대상 | geniefy 파일 |
|------|-------------|
| ADK 에이전트 구조 | `src/agent/geniefy_agent.py` |
| 도메인 에이전트 | `src/agent/domains/` |
| FastAPI 라이프사이클 | `src/api/main.py` |
| 이벤트 처리 | `src/services/event_processor.py` |

---

## 7. 핵심 성공 지표 (KPI)

| 단계 | 지표 | 목표 |
|------|------|------|
| MVP | 일일 수집 콘텐츠 | 20+ 건 |
| | 첫 구독 워크스페이스 | 10개 |
| 성장 | 주간 활성 사용자 | 100+ |
| | 다이제스트 CTR | 15%+ |
| | 신규 워크스페이스/주 | 5+ |
| 확장 | 총 워크스페이스 | 500+ |
| | 리드 전환율 | 3%+ |

---

## 8. 비용 추정 (월간)

| 항목 | 예상 비용 |
|------|-----------|
| Gemini API (요약 1000건/일) | ~$50 |
| Firestore | ~$10 |
| Cloud Run | ~$20 |
| Resend (뉴스레터, 선택) | 무료~$20 |
| **총** | **~$80/월** |

---

## 9. 리스크 및 대응

| 리스크 | 대응 방안 |
|--------|-----------|
| 콘텐츠 품질 저하 | 초기에는 수동 큐레이션 병행, 품질 피드백 루프 구축 |
| 저작권 이슈 | 요약 + 원문 링크 방식, 법률 검토 |
| LLM 비용 증가 | Flash 모델 활용, 캐싱, 배치 처리 |
| 스팸 인식 | 옵트인 철저, 구독 취소 쉽게 |
| 경쟁 서비스 | 맞춤화 기능으로 차별화 |

---

## 10. 참고 자료

- [GeekNews](https://news.hada.io/) - 벤치마크 서비스
- [Universal Content Subscriber](https://www.linkedin.com/posts/gb-jeong_...) - 영감을 준 서비스
- [Google ADK](https://github.com/google/adk-python) - 에이전트 프레임워크
- [Cognee](https://github.com/topoteretes/cognee) - AI 메모리/지식 그래프 플랫폼
- [Cognee + Google ADK 통합 가이드](https://www.cognee.ai/blog/integrations/google-adk-cognee-integration-build-agents-with-persistent-memory) - ADK 에이전트에 지속적 메모리 추가
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) - YouTube 자막 추출
- [yt_dlp_transcript](https://github.com/kkensuke/yt_dlp_transcript) - YouTube STT 폴백
