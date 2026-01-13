"""MCP session creation and management utilities.

This module provides async context managers for creating and managing
MCP (Model Context Protocol) sessions with the Playwright server.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def create_playwright_server_params() -> StdioServerParameters:
    """Create StdioServerParameters for Playwright MCP server.

    Returns:
        StdioServerParameters configured to launch Playwright MCP server via npx

    Example:
        params = create_playwright_server_params()
        # Use with stdio_client
    """
    return StdioServerParameters(
        command="npx",
        args=["@playwright/mcp@latest"],
    )


@asynccontextmanager
async def create_mcp_session() -> AsyncGenerator[ClientSession, None]:
    """Create and manage an MCP session lifecycle.

    This async context manager handles the full lifecycle of an MCP session:
    1. Launches the Playwright MCP server via npx
    2. Creates and initializes a ClientSession
    3. Yields the session for use
    4. Automatically cleans up on exit

    Yields:
        Initialized ClientSession ready for tool loading and agent creation

    Example:
        async with create_mcp_session() as session:
            tools = await load_mcp_tools(session)
            agent = create_agent(model="deepseek-chat", tools=tools)
            # Use agent...
    """
    server_parameters = create_playwright_server_params()

    async with stdio_client(server=server_parameters) as (reader, writer):
        async with ClientSession(read_stream=reader, write_stream=writer) as session:
            await session.initialize()
            yield session
