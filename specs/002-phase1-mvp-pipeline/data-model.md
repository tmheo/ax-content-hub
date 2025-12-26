# Data Model: Phase 1 MVP

**Branch**: `002-phase1-mvp-pipeline` | **Date**: 2025-12-26

## Overview

4개 핵심 엔티티로 콘텐츠 수집/처리/배포 파이프라인을 구성합니다.

```
Source ──1:N──► Content ──N:M──► Digest
                                    │
Subscription ◄──1:N────────────────┘
```

## Entities

### Source (콘텐츠 소스)

RSS 피드, YouTube 채널 등 콘텐츠를 수집할 소스 정보를 관리합니다.

```python
class SourceType(str, Enum):
    RSS = "rss"
    YOUTUBE = "youtube"

class Source(BaseModel):
    """콘텐츠 소스 정보"""

    id: str                          # 고유 ID (예: "src_001")
    name: str                        # 소스 이름 (예: "OpenAI Blog")
    type: SourceType                 # 소스 타입 (rss/youtube)
    url: str                         # 피드 URL 또는 채널 URL

    # 소스별 설정 (선택적)
    config: dict = {}                # 타입별 추가 설정
    category: str | None = None      # 카테고리 (예: "AI_RESEARCH")
    language: str = "en"             # 원문 언어

    # 상태 관리
    is_active: bool = True           # 활성화 여부
    last_fetched_at: datetime | None # 마지막 수집 시간
    fetch_error_count: int = 0       # 연속 실패 횟수

    # 메타데이터
    created_at: datetime
    updated_at: datetime
```

**Firestore Collection**: `sources`
**Index**: `is_active` (활성 소스만 조회)

### Content (수집/처리된 콘텐츠)

수집된 원본 콘텐츠와 처리 결과를 저장합니다.

```python
class ProcessingStatus(str, Enum):
    PENDING = "pending"        # 수집됨, 처리 대기
    PROCESSING = "processing"  # 처리 중
    COMPLETED = "completed"    # 처리 완료
    FAILED = "failed"          # 처리 실패
    SKIPPED = "skipped"        # 건너뜀 (예: 자막 없음)
    TIMEOUT = "timeout"        # 타임아웃

class Content(BaseModel):
    """수집/처리된 콘텐츠"""

    id: str                          # 고유 ID
    source_id: str                   # 소스 참조

    # 멱등성 키 (중복 방지)
    content_key: str                 # {source_id}:{sha256(normalized_url)}

    # 원본 정보
    original_url: str                # 원문 URL
    original_title: str              # 원문 제목
    original_body: str | None        # 원문 본문 (YouTube: 자막)
    original_language: str = "en"    # 원문 언어
    original_published_at: datetime | None  # 원문 발행일

    # 처리 결과 (번역/요약)
    title_ko: str | None = None      # 한국어 제목 (20자 이내)
    summary_ko: str | None = None    # 한국어 요약 (3문장)
    why_important: str | None = None # 중요성 설명 (1문장)

    # 스코어링
    relevance_score: float | None = None  # AX 관련성 (0.0~1.0)
    categories: list[str] = []            # 자동 분류된 카테고리

    # 처리 상태
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    processing_attempts: int = 0     # 처리 시도 횟수
    last_error: str | None = None    # 마지막 에러 메시지

    # 타임스탬프
    collected_at: datetime           # 수집 시간
    processed_at: datetime | None    # 처리 완료 시간

    # 인터랙션 (Phase 2+)
    # stats: ContentStats | None = None
```

**Firestore Collection**: `contents`
**Index**:
- `content_key` (중복 확인, unique)
- `source_id, collected_at` (소스별 최신 콘텐츠)
- `processing_status, collected_at` (처리 대기 콘텐츠)
- `relevance_score, processed_at` (다이제스트용)

### Subscription (구독 정보)

슬랙 채널별 구독 설정을 관리합니다.

```python
class DeliveryFrequency(str, Enum):
    REALTIME = "realtime"  # 즉시 발송 (Phase 2+)
    DAILY = "daily"        # 일일 다이제스트
    WEEKLY = "weekly"      # 주간 다이제스트 (Phase 2+)

class SubscriptionPreferences(BaseModel):
    """구독 선호도 설정"""

    frequency: DeliveryFrequency = DeliveryFrequency.DAILY
    delivery_time: str = "09:00"     # HH:MM 형식 (KST)
    categories: list[str] = []       # 관심 카테고리 (빈 = 전체)
    min_relevance: float = 0.3       # 최소 관련성 점수
    language: str = "ko"             # 발송 언어

class Subscription(BaseModel):
    """슬랙 채널 구독 설정"""

    id: str                          # 고유 ID
    platform: str = "slack"          # 플랫폼 (Phase 1: slack만)

    # 슬랙 설정
    platform_config: dict            # team_id, channel_id

    # 회사 연결 (Phase 3+ 맞춤화용)
    company_id: str | None = None

    # 선호도
    preferences: SubscriptionPreferences

    # 상태
    is_active: bool = True

    # 메타데이터
    created_at: datetime
    updated_at: datetime
```

**Firestore Collection**: `subscriptions`
**Index**:
- `is_active, preferences.delivery_time` (발송 대상 조회)
- `platform_config.channel_id` (채널별 조회)

### Digest (발송 이력)

발송된 다이제스트를 기록하여 중복 발송을 방지합니다.

```python
class Digest(BaseModel):
    """발송된 다이제스트 이력"""

    id: str                          # 고유 ID
    subscription_id: str             # 구독 참조

    # 멱등성 키 (일일 중복 방지)
    digest_key: str                  # {subscription_id}:{YYYY-MM-DD}

    # 콘텐츠 참조
    content_ids: list[str]           # 포함된 콘텐츠 ID 목록
    content_count: int               # 콘텐츠 개수

    # 발송 정보
    sent_at: datetime                # 발송 시간
    slack_message_ts: str | None     # 슬랙 메시지 타임스탬프 (수정/삭제용)

    # 인터랙션 (Phase 2+)
    # opened_at: datetime | None
    # clicks: list[ClickEvent] = []
```

**Firestore Collection**: `digests`
**Index**:
- `digest_key` (중복 확인, unique)
- `subscription_id, sent_at` (구독별 발송 이력)

## Utility Types

### URL 정규화

```python
def normalize_url(url: str) -> str:
    """URL 정규화 (멱등성 키 생성용)

    Rules:
    - scheme/host 소문자화
    - trailing '/' 제거
    - 추적 파라미터 제거 (utm_*, ref, fbclid, etc.)
    - fragment 제거
    """
    parsed = urlparse(url.lower())
    query = parse_qs(parsed.query)

    # 추적 파라미터 제거
    tracking_params = {'utm_source', 'utm_medium', 'utm_campaign',
                       'utm_term', 'utm_content', 'ref', 'fbclid',
                       'gclid', 'source', 'ref_src'}
    filtered_query = {k: v for k, v in query.items()
                      if k not in tracking_params}

    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path.rstrip('/'),
        '',
        urlencode(filtered_query, doseq=True),
        ''
    ))

def generate_content_key(source_id: str, url: str) -> str:
    """콘텐츠 멱등성 키 생성"""
    normalized = normalize_url(url)
    url_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"{source_id}:{url_hash}"

def generate_digest_key(subscription_id: str, date: date) -> str:
    """다이제스트 멱등성 키 생성"""
    return f"{subscription_id}:{date.isoformat()}"
```

## Validation Rules

### Source
- `url` must be valid HTTP(S) URL
- `type` must match URL pattern (youtube.com → youtube, else → rss)
- `fetch_error_count` >= 3 → auto-deactivate

### Content
- `content_key` must be unique
- `title_ko` must be <= 20 characters
- `relevance_score` must be 0.0 ~ 1.0
- `processing_attempts` > 3 → status = FAILED

### Subscription
- `platform_config.channel_id` must start with 'C'
- `preferences.delivery_time` must be HH:MM format
- `preferences.min_relevance` must be 0.0 ~ 1.0

### Digest
- `digest_key` must be unique
- `content_ids` must not be empty (except "no content" notification)

## State Transitions

### Content Processing Status

```
[New URL Discovered]
        │
        ▼
    PENDING ──(processing started)──► PROCESSING
        │                                 │
        │                           ┌─────┴─────┐
        │                           │           │
        │                    (success)    (failure)
        │                           │           │
        │                           ▼           ▼
        │                      COMPLETED     FAILED
        │                                       │
        │                               (retry < 3)
        │                                       │
        └───────────────────────────────────────┘

        ▼ (no caption)
     SKIPPED

        ▼ (timeout > 30s)
     TIMEOUT
```

## Sample Data

### Source Example
```json
{
  "id": "src_001",
  "name": "OpenAI Blog",
  "type": "rss",
  "url": "https://openai.com/blog/rss",
  "category": "AI_RESEARCH",
  "language": "en",
  "is_active": true,
  "last_fetched_at": "2025-12-26T09:00:00Z"
}
```

### Content Example
```json
{
  "id": "cnt_abc123",
  "source_id": "src_001",
  "content_key": "src_001:a1b2c3d4e5f6",
  "original_url": "https://openai.com/blog/gpt-5",
  "original_title": "Introducing GPT-5",
  "original_body": "Today we announce...",
  "title_ko": "GPT-5 공개: 추론 능력 대폭 향상",
  "summary_ko": "OpenAI가 새로운 모델 GPT-5를 공개했습니다. 기존 대비 추론 능력이 3배 향상되었습니다. 다양한 분야에서 활용 가능합니다.",
  "why_important": "기업 AI 도입 전략에 직접적 영향",
  "relevance_score": 0.95,
  "processing_status": "completed",
  "collected_at": "2025-12-26T08:00:00Z",
  "processed_at": "2025-12-26T08:03:00Z"
}
```

### Subscription Example
```json
{
  "id": "sub_001",
  "platform": "slack",
  "platform_config": {
    "team_id": "T12345",
    "channel_id": "C12345"
  },
  "preferences": {
    "frequency": "daily",
    "delivery_time": "09:00",
    "categories": [],
    "min_relevance": 0.3,
    "language": "ko"
  },
  "is_active": true
}
```

### Digest Example
```json
{
  "id": "dig_001",
  "subscription_id": "sub_001",
  "digest_key": "sub_001:2025-12-26",
  "content_ids": ["cnt_abc123", "cnt_def456"],
  "content_count": 2,
  "sent_at": "2025-12-26T09:00:15Z",
  "slack_message_ts": "1735203615.000100"
}
```
