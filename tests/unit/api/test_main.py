"""Tests for FastAPI main application."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def clear_module_cache() -> None:
    """Clear cached modules before each test."""
    # Remove cached modules to ensure fresh imports
    modules_to_remove = [key for key in sys.modules.keys() if key.startswith("src.api")]
    for module in modules_to_remove:
        del sys.modules[module]


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_returns_healthy(self) -> None:
        """GET /health should return healthy status."""
        # Mock dependencies before importing
        with (
            patch("src.config.logging.configure_logging"),
            patch(
                "src.config.settings.Settings",
                return_value=MagicMock(
                    GCP_PROJECT_ID="test-project",
                    SLACK_BOT_TOKEN="xoxb-test",
                    LOG_JSON=False,
                    is_local=True,
                ),
            ),
            patch("src.adapters.firestore_client.firestore"),
            patch("src.adapters.slack_client.WebClient"),
        ):
            from src.api.main import app

            client = TestClient(app)
            response = client.get("/health")

            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}

    def test_health_response_structure(self) -> None:
        """GET /health should include status field."""
        with (
            patch("src.config.logging.configure_logging"),
            patch(
                "src.config.settings.Settings",
                return_value=MagicMock(
                    GCP_PROJECT_ID="test-project",
                    SLACK_BOT_TOKEN="xoxb-test",
                    LOG_JSON=False,
                    is_local=True,
                ),
            ),
            patch("src.adapters.firestore_client.firestore"),
            patch("src.adapters.slack_client.WebClient"),
        ):
            from src.api.main import app

            client = TestClient(app)
            response = client.get("/health")

            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"


class TestAppMetadata:
    """Test application metadata."""

    def test_app_has_title(self) -> None:
        """App should have proper title."""
        with (
            patch("src.config.logging.configure_logging"),
            patch(
                "src.config.settings.Settings",
                return_value=MagicMock(
                    GCP_PROJECT_ID="test-project",
                    SLACK_BOT_TOKEN="xoxb-test",
                    LOG_JSON=False,
                    is_local=True,
                ),
            ),
            patch("src.adapters.firestore_client.firestore"),
            patch("src.adapters.slack_client.WebClient"),
        ):
            from src.api.main import app

            assert app.title == "AX Content Hub"

    def test_app_has_version(self) -> None:
        """App should have version."""
        with (
            patch("src.config.logging.configure_logging"),
            patch(
                "src.config.settings.Settings",
                return_value=MagicMock(
                    GCP_PROJECT_ID="test-project",
                    SLACK_BOT_TOKEN="xoxb-test",
                    LOG_JSON=False,
                    is_local=True,
                ),
            ),
            patch("src.adapters.firestore_client.firestore"),
            patch("src.adapters.slack_client.WebClient"),
        ):
            from src.api.main import app

            assert app.version == "0.1.0"
