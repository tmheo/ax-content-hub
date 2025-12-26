"""Cloud Tasks client with local direct execution mode."""

import json
from collections.abc import Callable
from typing import Any

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2


class TasksClient:
    """Client for Cloud Tasks with local execution fallback.

    In 'direct' mode, tasks are executed immediately (for local development).
    In 'cloud_tasks' mode, tasks are enqueued to Cloud Tasks.
    """

    def __init__(
        self,
        mode: str = "direct",
        project_id: str | None = None,
        location: str = "asia-northeast3",
        queue: str = "default",
        target_url: str | None = None,
        service_account_email: str | None = None,
    ) -> None:
        """Initialize Tasks client.

        Args:
            mode: 'direct' for local execution, 'cloud_tasks' for Cloud Tasks.
            project_id: GCP project ID (required for cloud_tasks mode).
            location: Cloud Tasks location.
            queue: Queue name.
            target_url: HTTP target URL for tasks.
            service_account_email: Service account for OIDC auth.

        Raises:
            ValueError: If cloud_tasks mode is missing required config.
        """
        self._mode = mode
        self._handlers: dict[str, Callable[[dict[str, Any]], None]] = {}

        if mode == "cloud_tasks":
            if not project_id:
                raise ValueError("project_id is required for cloud_tasks mode")
            if not target_url:
                raise ValueError("target_url is required for cloud_tasks mode")

            self._client = tasks_v2.CloudTasksClient()
            self._queue_path = self._client.queue_path(project_id, location, queue)
            self._target_url = target_url
            self._service_account_email = service_account_email

    def register_handler(
        self, task_type: str, handler: Callable[[dict[str, Any]], None]
    ) -> None:
        """Register a handler for direct mode execution.

        Args:
            task_type: Task type identifier.
            handler: Function to handle the task payload.
        """
        self._handlers[task_type] = handler

    def enqueue(
        self,
        task_type: str,
        payload: dict[str, Any],
        task_id: str | None = None,
        delay_seconds: int | None = None,
    ) -> str | None:
        """Enqueue a task for execution.

        Args:
            task_type: Task type identifier.
            payload: Task payload data.
            task_id: Optional task ID for deduplication.
            delay_seconds: Optional delay before execution.

        Returns:
            Task name in cloud_tasks mode, None in direct mode.

        Raises:
            ValueError: If task_type is unknown in direct mode.
        """
        if self._mode == "direct":
            self._execute_direct(task_type, payload)
            return None
        return self._enqueue_cloud_tasks(task_type, payload, task_id, delay_seconds)

    def _execute_direct(self, task_type: str, payload: dict[str, Any]) -> None:
        """Execute task immediately in direct mode."""
        if task_type not in self._handlers:
            raise ValueError(f"Unknown task type: {task_type}")
        self._handlers[task_type](payload)

    def _enqueue_cloud_tasks(
        self,
        task_type: str,
        payload: dict[str, Any],
        task_id: str | None,
        delay_seconds: int | None,
    ) -> str:
        """Enqueue task to Cloud Tasks."""
        import datetime

        task: dict[str, Any] = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{self._target_url}/{task_type}",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(payload).encode(),
            }
        }

        if self._service_account_email:
            task["http_request"]["oidc_token"] = {
                "service_account_email": self._service_account_email,
                "audience": self._target_url,
            }

        if task_id:
            task["name"] = f"{self._queue_path}/tasks/{task_id}"

        if delay_seconds:
            schedule_time = timestamp_pb2.Timestamp()
            schedule_time.FromDatetime(
                datetime.datetime.now(tz=datetime.UTC)
                + datetime.timedelta(seconds=delay_seconds)
            )
            task["schedule_time"] = schedule_time

        response = self._client.create_task(parent=self._queue_path, task=task)  # type: ignore[arg-type]
        return response.name
