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
