"""Slack API client."""

from typing import Any

from slack_sdk import WebClient


class SlackClient:
    """Client for Slack API operations."""

    def __init__(self, token: str) -> None:
        """Initialize Slack client.

        Args:
            token: Slack Bot OAuth token (xoxb-...).
        """
        self._client = WebClient(token=token)

    def post_message(
        self,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Post a message to a Slack channel.

        Args:
            channel: Channel ID (C...) or name (#channel).
            text: Plain text message (used as fallback for blocks).
            blocks: Optional Block Kit blocks.

        Returns:
            Slack API response.

        Raises:
            SlackApiError: If the API call fails.
        """
        response = self._client.chat_postMessage(
            channel=channel,
            text=text,
            blocks=blocks,
        )
        return dict(response)
