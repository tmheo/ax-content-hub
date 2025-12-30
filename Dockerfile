# syntax=docker/dockerfile:1
# Cloud Run용 Dockerfile - AX Content Hub

FROM python:3.12-slim

# 시스템 패키지 설치 (ffmpeg는 YouTube STT용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 의존성 파일 복사 및 설치
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# 소스 코드 복사
COPY src/ ./src/

# 환경 변수 설정
ENV PORT=8080
ENV PATH="/app/.venv/bin:$PATH"

# Cloud Run에서 권장하는 uvicorn 설정
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
