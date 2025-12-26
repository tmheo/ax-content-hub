"""Tests for Settings configuration."""

import pytest
from pydantic import ValidationError


class TestSettings:
    """Test Settings class."""

    def test_settings_loads_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings should load values from environment variables."""
        monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
        monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")

        from src.config.settings import Settings

        settings = Settings()

        assert settings.GCP_PROJECT_ID == "test-project"
        assert settings.GOOGLE_API_KEY == "test-api-key"
        assert settings.SLACK_BOT_TOKEN == "xoxb-test"
        assert settings.SLACK_SIGNING_SECRET == "test-secret"

    def test_settings_missing_required_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Settings should raise ValidationError when required vars are missing."""
        # Clear all required env vars
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)

        from src.config.settings import Settings

        with pytest.raises(ValidationError):
            # _env_file=None으로 .env 파일 로딩 비활성화
            Settings(_env_file=None)

    def test_settings_is_local_property(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """is_local should return True when FIRESTORE_EMULATOR_HOST is set."""
        monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
        monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
        monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "localhost:8086")

        from src.config.settings import Settings

        settings = Settings()
        assert settings.is_local is True

    def test_settings_is_local_false_when_no_emulator(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """is_local should return False when FIRESTORE_EMULATOR_HOST is not set."""
        monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
        monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
        monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)

        from src.config.settings import Settings

        # _env_file=None으로 .env 파일 로딩 비활성화 (FIRESTORE_EMULATOR_HOST 방지)
        settings = Settings(_env_file=None)
        assert settings.is_local is False

    def test_settings_default_tasks_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TASKS_MODE should default to 'direct'."""
        monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
        monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
        monkeypatch.delenv("TASKS_MODE", raising=False)

        from src.config.settings import Settings

        settings = Settings()
        assert settings.TASKS_MODE == "direct"
