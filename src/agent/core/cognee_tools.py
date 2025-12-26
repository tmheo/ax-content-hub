"""Cognee memory tools for Google ADK agents.

This module provides a wrapper around Cognee's memory tools for use with
Google ADK agents. It supports both global memory (shared across all sessions)
and sessionized memory (isolated per workspace/session).

Usage:
    # Global memory (single workspace)
    add_memory, search_memory = get_cognee_tools()

    # Sessionized memory (multi-workspace)
    add_memory, search_memory = get_cognee_tools(workspace_id="ws-123")
"""

from collections.abc import Callable
from typing import Any

# Try to import Cognee tools, fall back to stubs if not available
try:
    from cognee_integration_google_adk import (
        add_tool,
        get_sessionized_cognee_tools,
        search_tool,
    )
except ImportError:
    # Fallback stubs for when cognee-integration-google-adk is not installed
    def add_tool(content: str) -> dict[str, Any]:
        """Stub add_tool for when Cognee is not available."""
        return {"status": "stub", "message": "Cognee not installed"}

    def search_tool(query: str) -> list[dict[str, Any]]:
        """Stub search_tool for when Cognee is not available."""
        return []

    def get_sessionized_cognee_tools(
        session_id: str,
    ) -> tuple[Callable[..., Any], Callable[..., Any]]:
        """Stub get_sessionized_cognee_tools for when Cognee is not available."""
        return add_tool, search_tool


def get_cognee_tools(
    workspace_id: str | None = None,
) -> tuple[Callable[..., Any], Callable[..., Any]]:
    """Get Cognee memory tools for ADK agents.

    Args:
        workspace_id: Optional workspace/session ID for memory isolation.
            If provided, returns sessionized tools with isolated memory.
            If None, returns global shared memory tools.

    Returns:
        Tuple of (add_memory, search_memory) functions.

    Example:
        # In your agent
        add_memory, search_memory = get_cognee_tools("workspace-123")

        # Store information
        await add_memory("Important fact about AI trends 2024")

        # Search for related information
        results = await search_memory("AI trends")
    """
    if workspace_id:
        return get_sessionized_cognee_tools(workspace_id)
    return add_tool, search_tool
