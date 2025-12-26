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
