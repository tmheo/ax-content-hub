# AX Content Hub

AX(AI Transformation) 콘텐츠를 큐레이션하여 슬랙으로 전달하는 봇입니다.

## 핵심 가치

"읽어야 할 것"이 아니라 "이미 정리된 것"을 받는 경험

## 주요 기능

- **수집**: RSS 피드, YouTube 자막, 웹 스크래핑
- **처리**: 영→한 번역, GeekNews 스타일 요약, AX 관련성 스코어링
- **배포**: 슬랙 다이제스트 발송

## 기술 스택

- Python 3.12+ / uv
- FastAPI / Google ADK / Cognee
- Google Cloud: Firestore, Cloud Run, Cloud Scheduler, Cloud Tasks
- LLM: Gemini

## 빠른 시작

```bash
# 의존성 설치
uv sync --all-extras

# pre-commit 설정
uv run pre-commit install

# 개발 서버 시작
uv run uvicorn src.api.main:app --reload --port 8080
```

## 개발

```bash
# 테스트
uv run pytest tests/ -v

# 코드 품질
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/
uv run mypy src/
```

자세한 내용은 [CLAUDE.md](CLAUDE.md)를 참조하세요.
