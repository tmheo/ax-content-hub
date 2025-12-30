"""Application settings using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration from environment variables.

    All required settings must be provided via environment variables or .env file.
    Optional settings have default values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Google Cloud Platform
    # -------------------------------------------------------------------------
    GCP_PROJECT_ID: str

    # Firestore Emulator (local development)
    FIRESTORE_EMULATOR_HOST: str | None = None

    # -------------------------------------------------------------------------
    # Google AI (Gemini)
    # -------------------------------------------------------------------------
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-3-flash-preview"

    # -------------------------------------------------------------------------
    # Slack
    # -------------------------------------------------------------------------
    SLACK_BOT_TOKEN: str
    SLACK_SIGNING_SECRET: str

    # -------------------------------------------------------------------------
    # Cloud Tasks
    # -------------------------------------------------------------------------
    TASKS_MODE: str = "direct"  # "direct" or "cloud_tasks"
    TASKS_TARGET_URL: str | None = None
    TASKS_SERVICE_ACCOUNT_EMAIL: str | None = None

    # -------------------------------------------------------------------------
    # Content Pipeline (Phase 1)
    # -------------------------------------------------------------------------
    COLLECTION_INTERVAL_HOURS: int = 1  # RSS/YouTube 수집 주기 (시간)
    DIGEST_DELIVERY_TIME: str = "09:00"  # 다이제스트 발송 시간 (KST)
    MIN_RELEVANCE_SCORE: float = 0.3  # 다이제스트 포함 최소 관련성 점수
    PROCESSING_TIMEOUT_SECONDS: int = 30  # 콘텐츠 처리 타임아웃
    MAX_PROCESSING_RETRIES: int = 3  # 처리 최대 재시도 횟수

    # -------------------------------------------------------------------------
    # OIDC (Internal endpoints protection)
    # -------------------------------------------------------------------------
    OIDC_AUDIENCE: str | None = None  # Cloud Run service URL (프로덕션)

    # -------------------------------------------------------------------------
    # Web Scraping (Phase 2)
    # -------------------------------------------------------------------------
    SCRAPING_TIMEOUT_SECONDS: int = 60
    """웹 스크래핑 총 타임아웃"""

    SCRAPING_MIN_CONTENT_LENGTH: int = 200
    """최소 콘텐츠 길이 (자)"""

    SCRAPING_REQUEST_INTERVAL_MIN: float = 2.0
    """최소 요청 간격 (초)"""

    SCRAPING_REQUEST_INTERVAL_MAX: float = 5.0
    """최대 요청 간격 (초)"""

    # -------------------------------------------------------------------------
    # YouTube STT (Phase 2)
    # -------------------------------------------------------------------------
    STT_ENABLED: bool = True
    """STT 폴백 활성화 여부"""

    STT_MODEL_SIZE: str = "small"
    """Whisper 모델 크기 (tiny, base, small, medium)"""

    STT_COMPUTE_TYPE: str = "int8"
    """연산 타입 (int8, float16, float32)"""

    STT_MAX_VIDEO_DURATION_MINUTES: int = 30
    """STT 대상 최대 영상 길이 (분)"""

    # -------------------------------------------------------------------------
    # Quality Filtering (Phase 2)
    # -------------------------------------------------------------------------
    QUALITY_SIMILARITY_THRESHOLD: float = 0.85
    """중복 판단 유사도 임계값"""

    QUALITY_MAX_AGE_DAYS: int = 7
    """최신성 필터 기준일"""

    QUALITY_MIN_BODY_LENGTH: int = 100
    """최소 본문 길이 (자)"""

    QUALITY_REQUIRE_TITLE: bool = True
    """제목 필수 여부"""

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    LOG_JSON: bool = True

    @property
    def is_local(self) -> bool:
        """Check if running in local development mode."""
        return self.FIRESTORE_EMULATOR_HOST is not None


# Singleton instance (lazy initialization)
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the application settings (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
