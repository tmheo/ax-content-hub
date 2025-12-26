# Feature Specification: Phase 1 MVP - 핵심 파이프라인

**Feature Branch**: `002-phase1-mvp-pipeline`
**Created**: 2025-12-26
**Status**: Draft
**Input**: docs/ax-content-hub-plan.md Phase 1 섹션 - RSS + YouTube 수집 → LLM 요약 → 슬랙 전송 기본 루프 완성

## Clarifications (Resolved)

| 질문 | 결정 | 근거 |
|------|------|------|
| 콘텐츠 소스 범위 | RSS + YouTube만 (P0) | 웹 스크래핑은 Phase 2로 이관 |
| 요약 스타일 | GeekNews 스타일 | 핵심 가치 전달에 최적화 |
| 슬랙 배포 범위 | 단일 워크스페이스 | 멀티 워크스페이스는 Phase 3 |
| 스케줄러 빈도 | 수집 1시간마다, 배포 매일 09:00 | 운영 효율성과 사용자 경험 균형 |
| 중복 방지 전략 | content_key 기반 멱등성 | URL 해시로 중복 수집 방지 |

## Assumptions

- Phase 0에서 구현된 인프라 (Firestore, Slack, Tasks 클라이언트)가 동작 중
- Gemini API 키가 설정되어 있고 gemini-3-flash-preview 모델 사용 가능
- 슬랙 봇이 대상 채널에 메시지 전송 권한 보유
- 콘텐츠 소스(RSS 피드, YouTube 채널)가 사전에 등록되어 있음

## User Scenarios & Testing *(mandatory)*

### User Story 1 - RSS 피드 콘텐츠 수집 (Priority: P1)

운영자가 등록한 RSS 피드(예: OpenAI Blog, Anthropic News)에서 새로운 글이 발행되면,
시스템이 자동으로 해당 콘텐츠를 수집하고 Firestore에 저장한다.
중복 수집을 방지하여 동일한 글이 여러 번 처리되지 않는다.

**Why this priority**: 콘텐츠 파이프라인의 시작점으로, 이후 모든 처리의 기반이 됨

**Independent Test**: RSS 피드 URL을 등록하고 수집 트리거 호출 시, 새 콘텐츠가 Firestore에 저장되는지 확인

**Acceptance Scenarios**:

1. **Given** RSS 소스가 등록된 상태, **When** 수집 트리거 실행, **Then** 피드의 새 글이 contents 컬렉션에 저장됨
2. **Given** 이미 수집된 URL, **When** 동일 URL 재수집 시도, **Then** 중복 저장되지 않음 (content_key로 확인)
3. **Given** RSS 피드에 10개의 새 글, **When** 수집 실행, **Then** 모든 10개가 pending 상태로 저장됨
4. **Given** 피드 URL이 유효하지 않음, **When** 수집 시도, **Then** 에러 로깅 후 다음 소스로 진행

---

### User Story 2 - YouTube 자막 수집 (Priority: P1)

등록된 YouTube 채널의 새 영상에서 기존 자막을 추출하여 텍스트로 저장한다.
자막이 없는 영상은 별도 표시하고 (Phase 2 STT 폴백 대상), 현재는 건너뛴다.

**Why this priority**: 영상 콘텐츠 접근성을 높이는 핵심 기능

**Independent Test**: YouTube 영상 ID를 입력하면 자막 텍스트가 추출되어 저장되는지 확인

**Acceptance Scenarios**:

1. **Given** 영어 자막이 있는 YouTube 영상, **When** 자막 수집 실행, **Then** 전체 자막 텍스트가 contents에 저장됨
2. **Given** 한국어 자막이 있는 영상, **When** 자막 수집 실행, **Then** 한국어 자막이 우선 추출됨
3. **Given** 자막이 없는 영상, **When** 수집 시도, **Then** processing_status=skipped로 저장되고 에러 없이 계속 진행
4. **Given** 이미 수집된 영상 ID, **When** 재수집 시도, **Then** 중복 저장되지 않음

---

### User Story 3 - 콘텐츠 번역 및 GeekNews 스타일 요약 (Priority: P1)

수집된 영문 콘텐츠를 한국어로 번역하고, GeekNews 스타일로 요약하여
핵심 가치를 20자 이내 제목과 3문장 이내 요약으로 제공한다.
"왜 중요한지"를 1문장으로 추가하여 독자가 빠르게 가치를 판단할 수 있게 한다.

**Why this priority**: 사용자에게 전달되는 콘텐츠의 품질을 결정하는 핵심 처리

**Independent Test**: 영문 콘텐츠 입력 시 한국어 제목/요약/중요성이 생성되는지 확인

**Acceptance Scenarios**:

1. **Given** 영문 제목과 본문, **When** 요약 처리 실행, **Then** title_ko(20자 이내), summary_ko(3문장), why_important(1문장) 생성됨
2. **Given** 이미 한국어인 콘텐츠, **When** 처리 실행, **Then** 번역 없이 요약만 수행됨
3. **Given** 매우 긴 본문(10,000자 이상), **When** 처리 실행, **Then** 정상적으로 요약 완료됨
4. **Given** LLM 응답이 JSON 파싱 실패, **When** 재시도 로직 적용, **Then** 최대 3회 재시도 후 원본 유지

---

### User Story 4 - AX 관련성 스코어링 (Priority: P1)

콘텐츠가 AI Transformation(AX)과 얼마나 관련 있는지 0.0~1.0 점수로 평가한다.
점수 기준을 투명하게 정의하고, 낮은 점수(0.3 미만)의 콘텐츠는 발송에서 제외한다.

**Why this priority**: 품질 필터링으로 사용자에게 관련 있는 콘텐츠만 전달

**Independent Test**: 다양한 주제의 콘텐츠에 대해 일관된 점수가 산출되는지 확인

**Acceptance Scenarios**:

1. **Given** AI 관련 콘텐츠(예: GPT-5 발표), **When** 스코어링 실행, **Then** relevance_score >= 0.7
2. **Given** AI 무관 콘텐츠(예: 요리 레시피), **When** 스코어링 실행, **Then** relevance_score < 0.3
3. **Given** 콘텐츠 처리 완료, **When** Firestore 저장, **Then** relevance_score 필드가 포함됨
4. **Given** 스코어 0.3 미만, **When** 다이제스트 생성, **Then** 해당 콘텐츠 제외됨

---

### User Story 5 - 슬랙 다이제스트 발송 (Priority: P1)

처리 완료된 콘텐츠를 모아 슬랙 채널에 일일 다이제스트로 발송한다.
Block Kit 포맷을 사용하여 깔끔하게 표시하고, 원문 링크를 제공한다.
동일 날짜에 중복 발송을 방지한다.

**Why this priority**: 사용자에게 가치를 전달하는 최종 단계

**Independent Test**: 처리된 콘텐츠 3건으로 다이제스트 생성 후 슬랙에 메시지 전송 확인

**Acceptance Scenarios**:

1. **Given** 처리된 콘텐츠 5건, **When** 배포 트리거 실행, **Then** 슬랙 채널에 다이제스트 메시지 전송됨
2. **Given** 다이제스트에 콘텐츠 50건 초과, **When** 발송 시도, **Then** Slack 50 blocks 제한 대응하여 분할 발송
3. **Given** 오늘 이미 발송됨(digest_key 존재), **When** 재발송 시도, **Then** 중복 발송되지 않음
4. **Given** 발송할 콘텐츠가 0건, **When** 배포 트리거 실행, **Then** "오늘 새로운 콘텐츠가 없습니다" 메시지 전송

---

### User Story 6 - 스케줄러 기반 자동화 파이프라인 (Priority: P1)

Cloud Scheduler가 수집과 배포를 자동으로 트리거한다.
수집은 1시간마다, 배포는 매일 오전 9시에 실행된다.
각 엔드포인트는 Cloud Run IAM으로 보호되어 외부 호출을 차단한다.

**Why this priority**: 운영 자동화로 수동 개입 없이 서비스 운영 가능

**Independent Test**: Cloud Scheduler 설정 후 예정된 시간에 자동 실행되는지 로그 확인

**Acceptance Scenarios**:

1. **Given** 스케줄러 설정 완료, **When** 정시(매시 정각) 도달, **Then** /internal/collect 엔드포인트 호출됨
2. **Given** 스케줄러 설정 완료, **When** 매일 09:00 도달, **Then** /internal/distribute 엔드포인트 호출됨
3. **Given** OIDC 토큰 없는 요청, **When** /internal/* 호출 시도, **Then** 401/403 에러 반환
4. **Given** 유효한 OIDC 토큰, **When** /internal/collect 호출, **Then** 수집 파이프라인 정상 실행

---

### User Story 7 - 콘텐츠 소스 관리 (Priority: P2)

운영자가 RSS 피드 URL이나 YouTube 채널을 콘텐츠 소스로 등록/수정/삭제할 수 있다.
각 소스는 활성/비활성 상태를 가지며, 비활성 소스는 수집에서 제외된다.

**Why this priority**: MVP 이후 소스 확장을 위한 기반

**Independent Test**: API를 통해 소스 CRUD 후 Firestore에 반영되는지 확인

**Acceptance Scenarios**:

1. **Given** 새 RSS URL, **When** 소스 등록 API 호출, **Then** sources 컬렉션에 저장됨
2. **Given** 등록된 소스, **When** is_active=false 설정, **Then** 수집에서 제외됨
3. **Given** 소스 목록 조회, **When** API 호출, **Then** 모든 등록된 소스 반환

---

### User Story 8 - 구독 관리 (Priority: P2)

슬랙 채널별 구독 설정을 관리한다.
구독에는 배포 시간, 관심 카테고리, 최소 관련성 점수 등의 선호도를 설정할 수 있다.

**Why this priority**: 향후 맞춤화 기능의 기반

**Independent Test**: 구독 등록 후 해당 채널에 다이제스트가 발송되는지 확인

**Acceptance Scenarios**:

1. **Given** 채널 ID와 선호도, **When** 구독 등록, **Then** subscriptions 컬렉션에 저장됨
2. **Given** 구독에 min_relevance=0.8 설정, **When** 다이제스트 생성, **Then** 0.8 이상 콘텐츠만 포함
3. **Given** 구독 비활성화, **When** 배포 시간 도달, **Then** 해당 채널에 발송 안됨

---

### Edge Cases

- RSS 피드가 일시적으로 다운된 경우: 에러 로깅 후 다음 소스로 진행, 24시간 후 자동 재시도
- YouTube API 할당량 초과: 에러 로깅 후 대기, 다음 수집 주기에 재시도
- LLM 응답 지연(30초 초과): 타임아웃 후 원본 데이터 유지, processing_status=timeout
- 슬랙 rate limit 도달: 지수 백오프로 재시도 (최대 5회)
- 콘텐츠 본문이 비어있는 경우: 제목만으로 요약 시도, 불가 시 건너뜀
- Firestore 쓰기 실패: Cloud Tasks로 재시도 큐잉
- 모든 소스가 비활성인 경우: 경고 로그 출력, 수집 스킵
- 동시에 여러 수집 트리거 실행: content_key 기반 멱등성으로 중복 방지

## Requirements *(mandatory)*

### Functional Requirements

**수집 (Collect)**
- **FR-001**: 시스템 MUST RSS 피드에서 콘텐츠 자동 수집 가능 (feedparser 활용)
- **FR-002**: 시스템 MUST YouTube 영상에서 기존 자막 추출 가능 (youtube-transcript-api 활용)
- **FR-003**: 시스템 MUST URL 기반 content_key로 중복 수집 방지
- **FR-004**: 시스템 MUST 수집 실패 시 에러 로깅 후 다음 소스로 진행

**처리 (Process)**
- **FR-005**: 시스템 MUST 영문 콘텐츠를 한국어로 번역
- **FR-006**: 시스템 MUST GeekNews 스타일 요약 생성 (제목 20자, 요약 3문장, 중요성 1문장)
- **FR-007**: 시스템 MUST AX 관련성 점수(0.0~1.0) 산출
- **FR-008**: 시스템 MUST LLM 응답 JSON 파싱 실패 시 최대 3회 재시도
- **FR-009**: 시스템 MUST 처리 상태(pending/processing/completed/failed) 추적

**배포 (Distribute)**
- **FR-010**: 시스템 MUST 슬랙 Block Kit 형식으로 다이제스트 메시지 구성
- **FR-011**: 시스템 MUST 원문 링크 포함
- **FR-012**: 시스템 MUST Slack 50 blocks 제한 시 분할 발송
- **FR-013**: 시스템 MUST digest_key로 일일 중복 발송 방지

**스케줄링**
- **FR-014**: 시스템 MUST Cloud Scheduler로 수집 1시간마다 트리거
- **FR-015**: 시스템 MUST Cloud Scheduler로 배포 매일 09:00 트리거
- **FR-016**: 시스템 MUST /internal/* 엔드포인트를 OIDC 토큰으로 보호

**데이터 관리**
- **FR-017**: 시스템 MUST sources 컬렉션에서 소스 CRUD 제공
- **FR-018**: 시스템 MUST subscriptions 컬렉션에서 구독 CRUD 제공
- **FR-019**: 시스템 MUST contents 컬렉션에 수집/처리 결과 저장
- **FR-020**: 시스템 MUST digests 컬렉션에 발송 이력 저장

### Key Entities

- **Source**: 콘텐츠 소스 정보 (id, name, type[rss/youtube], url, config, category, is_active, last_fetched_at)
- **Content**: 수집/처리된 콘텐츠 (id, source_id, content_key, original_url, original_title, title_ko, summary_ko, why_important, relevance_score, processing_status, collected_at, processed_at)
- **Subscription**: 슬랙 채널 구독 설정 (id, platform_config, preferences[frequency, categories, min_relevance], is_active)
- **Digest**: 발송된 다이제스트 (id, subscription_id, digest_key, content_ids, sent_at)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 시스템이 등록된 RSS 피드에서 1시간 이내에 새 콘텐츠를 수집함
- **SC-002**: 수집된 콘텐츠의 95% 이상이 5분 이내에 번역/요약 처리 완료됨
- **SC-003**: 다이제스트가 매일 09:00에 5분 오차 이내로 발송됨
- **SC-004**: 중복 수집률 0% (동일 URL 재수집 없음)
- **SC-005**: 중복 발송률 0% (동일 날짜 재발송 없음)
- **SC-006**: AX 관련성 점수의 일관성 (유사 콘텐츠에 대해 ±0.1 이내 편차)
- **SC-007**: 일일 수집 콘텐츠 20건 이상 (충분한 소스 등록 시)
- **SC-008**: 슬랙 다이제스트 전송 성공률 99% 이상
- **SC-009**: 전체 파이프라인(수집→처리→발송) 단위 테스트 커버리지 80% 이상
