"""Agent creation and configuration utilities.

This module provides functions for creating agents for all pipeline phases:
planning, extraction, and aggregation.
"""

import logging
from typing import Any

from langchain.agents import create_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession

from schemas import ArticleExtraction, PlanningOutput, AggregationOutput


def create_planning_agent(
    *,
    model: str = "deepseek-chat",
    debug: bool = False,
) -> Any:
    """Create a planning agent without tools.

    The planning agent selects relevant news sources based on the topic.
    It doesn't need browser tools, just structured output generation.

    Args:
        model: Model identifier (default: "deepseek-chat")
        debug: Enable debug mode for agent (default: False)

    Returns:
        Configured agent ready for invocation

    Example:
        agent = create_planning_agent()
        response = await agent.ainvoke(planning_prompt)
    """
    agent = create_agent(
        model=model,
        tools=[],  # No tools needed for planning
        response_format=PlanningOutput,
        debug=debug,
    )

    return agent


async def create_extraction_agent(
    session: ClientSession,
    *,
    model: str = "deepseek-chat",
    debug: bool = False,
) -> Any:
    """Create an extraction agent with MCP tools.

    This function loads tools from an MCP session and creates an agent
    configured for news article extraction. The agent uses Playwright tools
    for browser automation.

    Args:
        session: Active MCP ClientSession
        model: Model identifier (default: "deepseek-chat")
        response_format: Pydantic model for structured output
        debug: Enable debug mode for agent (default: False)

    Returns:
        Configured agent ready for invocation

    Example:
        async with create_mcp_session() as session:
            agent = await create_extraction_agent(session, debug=True)
            response = await agent.ainvoke(prompt)
    """
    tools = await load_mcp_tools(session)

    agent = create_agent(
        model=model,
        tools=tools,
        response_format=ArticleExtraction,
        debug=debug,
    )

    return agent


def create_aggregation_agent(
    *,
    model: str = "deepseek-chat",
    debug: bool = False,
) -> Any:
    """Create an aggregation agent without tools.

    The aggregation agent synthesizes extraction results into a comparison
    table and summary. It doesn't need browser tools, only structured output.

    Args:
        model: Model identifier (default: "deepseek-chat")
        debug: Enable debug mode for agent (default: False)

    Returns:
        Configured agent ready for invocation

    Example:
        agent = create_aggregation_agent()
        response = await agent.ainvoke(aggregation_prompt)
    """
    agent = create_agent(
        model=model,
        tools=[],  # No tools needed for aggregation
        response_format=AggregationOutput,
        debug=debug,
    )

    return agent
