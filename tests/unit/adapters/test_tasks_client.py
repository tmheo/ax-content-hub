"""Tests for Cloud Tasks client."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestTasksClient:
    """Test TasksClient class."""

    def test_direct_mode_executes_immediately(self) -> None:
        """In direct mode, tasks should execute immediately."""
        from src.adapters.tasks_client import TasksClient

        executed = []

        def handler(payload: dict[str, Any]) -> None:
            executed.append(payload)

        client = TasksClient(mode="direct")
        client.register_handler("test_task", handler)
        client.enqueue("test_task", {"key": "value"})

        assert len(executed) == 1
        assert executed[0] == {"key": "value"}

    def test_direct_mode_unknown_task_raises_error(self) -> None:
        """In direct mode, unknown task type should raise ValueError."""
        from src.adapters.tasks_client import TasksClient

        client = TasksClient(mode="direct")

        with pytest.raises(ValueError, match="Unknown task type"):
            client.enqueue("unknown_task", {"key": "value"})

    def test_cloud_tasks_mode_creates_task(self) -> None:
        """In cloud_tasks mode, should create Cloud Tasks task."""
        mock_client = MagicMock()

        with patch("google.cloud.tasks_v2.CloudTasksClient", return_value=mock_client):
            from src.adapters.tasks_client import TasksClient

            client = TasksClient(
                mode="cloud_tasks",
                project_id="test-project",
                location="asia-northeast3",
                queue="default",
                target_url="https://example.com/tasks",
                service_account_email="sa@test.iam.gserviceaccount.com",
            )
            client.enqueue("test_task", {"key": "value"}, task_id="task-123")

            mock_client.create_task.assert_called_once()
            call_args = mock_client.create_task.call_args
            assert "parent" in call_args.kwargs
            assert "task" in call_args.kwargs

    def test_cloud_tasks_mode_requires_config(self) -> None:
        """In cloud_tasks mode, missing config should raise ValueError."""
        from src.adapters.tasks_client import TasksClient

        with pytest.raises(ValueError, match="project_id is required"):
            TasksClient(mode="cloud_tasks")
