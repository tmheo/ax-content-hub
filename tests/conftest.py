"""Pytest configuration and shared fixtures."""

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(autouse=True)
def set_test_env() -> None:
    """Set test environment variables."""
    os.environ.setdefault("GCP_PROJECT_ID", "test-project")
    os.environ.setdefault("GOOGLE_API_KEY", "test-api-key")
    os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test-token")
    os.environ.setdefault("SLACK_SIGNING_SECRET", "test-signing-secret")
    os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "localhost:8086")
    os.environ.setdefault("TASKS_MODE", "direct")


@pytest.fixture
def mock_firestore_client() -> MagicMock:
    """Mock Firestore client."""
    client = MagicMock()
    client.collection.return_value.document.return_value.get = AsyncMock(
        return_value=MagicMock(exists=True, to_dict=lambda: {"test": "data"})
    )
    client.collection.return_value.document.return_value.set = AsyncMock()
    client.collection.return_value.document.return_value.update = AsyncMock()
    client.collection.return_value.document.return_value.delete = AsyncMock()
    return client


@pytest.fixture
def mock_slack_client() -> MagicMock:
    """Mock Slack client."""
    client = MagicMock()
    client.chat_postMessage = AsyncMock(
        return_value={"ok": True, "ts": "1234567890.123456"}
    )
    return client


@pytest.fixture
def sample_content() -> dict[str, Any]:
    """Sample content data for testing."""
    return {
        "id": "cnt_test123",
        "source_id": "src_001",
        "original_url": "https://example.com/article",
        "original_title": "Test Article",
        "title_ko": "테스트 기사",
        "summary_ko": "이것은 테스트 요약입니다.",
        "relevance_score": 0.85,
    }
