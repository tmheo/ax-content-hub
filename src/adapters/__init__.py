"""External service adapters."""

from src.adapters.firestore_client import FirestoreClient
from src.adapters.slack_client import SlackClient
from src.adapters.tasks_client import TasksClient

__all__ = [
    "FirestoreClient",
    "SlackClient",
    "TasksClient",
]
