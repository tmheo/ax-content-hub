# Quickstart: Phase 1 MVP - 핵심 파이프라인

## 사전 요구사항

- Python 3.12+
- uv (패키지 관리자)
- Docker (Firestore 에뮬레이터)
- GCP 프로젝트 (Gemini API, Cloud Run)

## 환경 설정

### 1. 의존성 설치

```bash
# Phase 1 의존성 추가
uv add feedparser youtube-transcript-api google-genai

# 개발 의존성
uv add --dev pytest-asyncio respx

# 전체 설치
uv sync --all-extras
```

### 2. 환경 변수 설정

```bash
# .env 파일 생성
cat > .env << 'EOF'
# GCP
GCP_PROJECT_ID=your-project-id

# Gemini
GOOGLE_API_KEY=your-gemini-api-key

# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret

# Cloud Tasks (로컬에서는 direct 모드)
TASKS_MODE=direct
EOF
```

### 3. Firestore 에뮬레이터 시작

```bash
docker compose up -d
```

### 4. 개발 서버 시작

```bash
uv run uvicorn src.api.main:app --reload --port 8080
```

## 핵심 사용 시나리오

### 소스 등록

```bash
# RSS 피드 등록
curl -X POST http://localhost:8080/api/sources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenAI Blog",
    "type": "rss",
    "url": "https://openai.com/blog/rss",
    "category": "AI_RESEARCH"
  }'

# YouTube 채널 등록
curl -X POST http://localhost:8080/api/sources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AI Explained",
    "type": "youtube",
    "url": "https://www.youtube.com/@aiexplained-official",
    "category": "AI_EDUCATION"
  }'
```

### 구독 등록

```bash
curl -X POST http://localhost:8080/api/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "platform_config": {
      "team_id": "T12345",
      "channel_id": "C12345"
    },
    "preferences": {
      "frequency": "daily",
      "delivery_time": "09:00",
      "min_relevance": 0.3
    }
  }'
```

### 수동 수집 트리거

```bash
# 로컬에서 수집 테스트
curl -X POST http://localhost:8080/internal/collect
```

### 수동 배포 트리거

```bash
# 로컬에서 다이제스트 발송 테스트
curl -X POST http://localhost:8080/internal/distribute
```

## 테스트 실행

```bash
# 전체 테스트
uv run pytest tests/ -v

# 특정 도메인 테스트
uv run pytest tests/unit/agent/domains/collector/ -v

# 통합 테스트
uv run pytest tests/integration/ -v

# 커버리지
uv run pytest --cov=src tests/
```

## 코드 품질 검사

```bash
# Ruff 린팅 + 포맷팅
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/

# MyPy 타입 체크
uv run mypy src/

# pre-commit (전체)
uv run pre-commit run --all-files
```

## 프로덕션 배포

### Cloud Run 배포

```bash
# Docker 이미지 빌드
docker build -t gcr.io/$GCP_PROJECT_ID/ax-content-hub .

# 이미지 푸시
docker push gcr.io/$GCP_PROJECT_ID/ax-content-hub

# Cloud Run 배포
gcloud run deploy ax-content-hub-api \
  --image gcr.io/$GCP_PROJECT_ID/ax-content-hub \
  --region asia-northeast3 \
  --no-allow-unauthenticated
```

### Cloud Scheduler 설정

```bash
# 수집 스케줄러 (1시간마다)
gcloud scheduler jobs create http trigger-collection \
  --schedule="0 * * * *" \
  --uri="https://ax-content-hub-api-xxxxx.run.app/internal/collect" \
  --http-method=POST \
  --oidc-service-account-email=scheduler-sa@$GCP_PROJECT_ID.iam.gserviceaccount.com

# 배포 스케줄러 (매일 09:00 KST)
gcloud scheduler jobs create http trigger-distribution \
  --schedule="0 0 * * *" \
  --time-zone="Asia/Seoul" \
  --uri="https://ax-content-hub-api-xxxxx.run.app/internal/distribute" \
  --http-method=POST \
  --oidc-service-account-email=scheduler-sa@$GCP_PROJECT_ID.iam.gserviceaccount.com
```

## 파이프라인 흐름

```
1. Cloud Scheduler (매시 정각)
   └─► POST /internal/collect
       └─► CollectorAgent: 소스별 새 콘텐츠 수집
           └─► Firestore: contents (status=pending)

2. Cloud Tasks (자동 큐잉)
   └─► POST /internal/tasks/process
       └─► ProcessorAgent: 번역 + 요약 + 스코어링
           └─► Firestore: contents (status=completed)

3. Cloud Scheduler (매일 09:00)
   └─► POST /internal/distribute
       └─► DistributorAgent: 다이제스트 생성 + 발송
           └─► Slack: 채널에 메시지 전송
           └─► Firestore: digests (발송 이력)
```

## 트러블슈팅

### Gemini API 오류

```bash
# API 키 확인
echo $GOOGLE_API_KEY

# 테스트 호출
curl "https://generativelanguage.googleapis.com/v1beta/models?key=$GOOGLE_API_KEY"
```

### Slack 발송 실패

```bash
# 봇 토큰 권한 확인
# - chat:write (메시지 전송)
# - channels:read (채널 목록)

# 채널 가입 확인
# 봇이 해당 채널에 추가되어 있어야 함
```

### YouTube 자막 없음

```bash
# 자막 가용성 확인
python -c "
from youtube_transcript_api import YouTubeTranscriptApi
try:
    t = YouTubeTranscriptApi.get_transcript('VIDEO_ID', languages=['en', 'ko'])
    print('Transcript available')
except Exception as e:
    print(f'No transcript: {e}')
"
```

### Firestore 에뮬레이터 연결

```bash
# 에뮬레이터 상태 확인
curl http://localhost:8089/

# 환경 변수 확인
export FIRESTORE_EMULATOR_HOST=localhost:8089
```

## 다음 단계

- Phase 2: 웹 스크래핑, YouTube STT 폴백
- Phase 3: 멀티 워크스페이스, 맞춤 인사이트
- Phase 4: 분석 API, 리드 수집
