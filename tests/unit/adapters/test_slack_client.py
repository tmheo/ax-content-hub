"""Tests for Slack client."""

from unittest.mock import MagicMock, patch

import pytest


class TestSlackClient:
    """Test SlackClient class."""

    @pytest.fixture
    def mock_web_client(self) -> MagicMock:
        """Create a mock Slack WebClient."""
        mock_client = MagicMock()
        # Slack SDK의 SlackResponse는 .data 속성으로 dict 반환
        mock_response = MagicMock()
        mock_response.data = {
            "ok": True,
            "ts": "1234567890.123456",
            "channel": "C12345678",
        }
        mock_client.chat_postMessage.return_value = mock_response
        return mock_client

    def test_post_message_success(self, mock_web_client: MagicMock) -> None:
        """post_message should send message and return response."""
        with patch("src.adapters.slack_client.WebClient", return_value=mock_web_client):
            from src.adapters.slack_client import SlackClient

            client = SlackClient(token="xoxb-test-token")
            result = client.post_message(
                channel="C12345678",
                text="Hello, World!",
            )

            assert result["ok"] is True
            assert result["ts"] == "1234567890.123456"
            mock_web_client.chat_postMessage.assert_called_once_with(
                channel="C12345678",
                text="Hello, World!",
                blocks=None,
                thread_ts=None,
            )

    def test_post_message_with_blocks(self, mock_web_client: MagicMock) -> None:
        """post_message should support Block Kit blocks."""
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Hello*"},
            }
        ]

        with patch("src.adapters.slack_client.WebClient", return_value=mock_web_client):
            from src.adapters.slack_client import SlackClient

            client = SlackClient(token="xoxb-test-token")
            client.post_message(
                channel="C12345678",
                text="Fallback text",
                blocks=blocks,
            )

            mock_web_client.chat_postMessage.assert_called_once_with(
                channel="C12345678",
                text="Fallback text",
                blocks=blocks,
                thread_ts=None,
            )

    def test_post_message_error(self, mock_web_client: MagicMock) -> None:
        """post_message should raise SlackApiError on failure."""
        from slack_sdk.errors import SlackApiError

        mock_web_client.chat_postMessage.side_effect = SlackApiError(
            message="channel_not_found",
            response={"ok": False, "error": "channel_not_found"},
        )

        with patch("src.adapters.slack_client.WebClient", return_value=mock_web_client):
            from src.adapters.slack_client import SlackClient

            client = SlackClient(token="xoxb-test-token")

            with pytest.raises(SlackApiError):
                client.post_message(
                    channel="C_invalid",
                    text="Hello",
                )
