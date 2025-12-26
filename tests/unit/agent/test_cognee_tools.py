"""Tests for Cognee memory tools."""

from unittest.mock import MagicMock, patch


class TestCogneeTools:
    """Test Cognee tools wrapper."""

    def test_get_cognee_tools_without_session(self) -> None:
        """get_cognee_tools without session_id should return global tools."""
        mock_add = MagicMock()
        mock_search = MagicMock()
        mock_tools = {
            "add_tool": mock_add,
            "search_tool": mock_search,
            "get_sessionized_cognee_tools": MagicMock(),
        }

        with patch(
            "src.agent.core.cognee_tools._get_cognee_imports",
            return_value=mock_tools,
        ):
            from src.agent.core.cognee_tools import get_cognee_tools

            add_memory, search_memory = get_cognee_tools()

            assert add_memory is mock_add
            assert search_memory is mock_search

    def test_get_cognee_tools_with_session(self) -> None:
        """get_cognee_tools with session_id should return sessionized tools."""
        mock_sessionized_add = MagicMock()
        mock_sessionized_search = MagicMock()
        mock_get_sessionized = MagicMock(
            return_value=(mock_sessionized_add, mock_sessionized_search)
        )
        mock_tools = {
            "add_tool": MagicMock(),
            "search_tool": MagicMock(),
            "get_sessionized_cognee_tools": mock_get_sessionized,
        }

        with patch(
            "src.agent.core.cognee_tools._get_cognee_imports",
            return_value=mock_tools,
        ):
            from src.agent.core.cognee_tools import get_cognee_tools

            add_memory, search_memory = get_cognee_tools(workspace_id="ws-123")

            mock_get_sessionized.assert_called_once_with("ws-123")
            assert add_memory is mock_sessionized_add
            assert search_memory is mock_sessionized_search

    def test_cognee_tools_are_callable(self) -> None:
        """Cognee tools should be callable functions."""
        mock_add = MagicMock()
        mock_search = MagicMock()
        mock_tools = {
            "add_tool": mock_add,
            "search_tool": mock_search,
            "get_sessionized_cognee_tools": MagicMock(),
        }

        with patch(
            "src.agent.core.cognee_tools._get_cognee_imports",
            return_value=mock_tools,
        ):
            from src.agent.core.cognee_tools import get_cognee_tools

            add_memory, search_memory = get_cognee_tools()

            # Should be callable
            assert callable(add_memory)
            assert callable(search_memory)
