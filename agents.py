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
    response_format: type = PlanningOutput,
) -> Any:
    """Create a planning agent without tools.

    The planning agent selects relevant news sources based on the topic.
    It doesn't need browser tools, just structured output generation.

    Args:
        model: Model identifier (default: "deepseek-chat")
        response_format: Pydantic model for structured output (default: PlanningOutput)

    Returns:
        Configured agent ready for invocation

    Example:
        agent = create_planning_agent()
        response = await agent.ainvoke(planning_prompt)
    """
    agent = create_agent(
        model=model,
        tools=[],  # No tools needed for planning
        response_format=response_format,
    )

    return agent


async def create_extraction_agent(
    session: ClientSession,
    *,
    model: str = "deepseek-chat",
    response_format: type = ArticleExtraction,
    debug: bool = False,
    logger: logging.Logger | None = None,
) -> Any:
    """Create an extraction agent with MCP tools.

    This function loads tools from an MCP session and creates an agent
    configured for news article extraction. The agent uses Playwright tools
    for browser automation.

    Args:
        session: Active MCP ClientSession
        model: Model identifier (default: "deepseek-chat")
        response_format: Pydantic model for structured output
        debug: Enable debug mode for agent (logs tool calls)
        logger: Optional logger for verbose output

    Returns:
        Configured agent ready for invocation

    Example:
        async with create_mcp_session() as session:
            agent = await create_extraction_agent(session, debug=True)
            response = await agent.ainvoke(prompt)
    """
    if logger:
        logger.debug("Loading MCP tools from session")

    tools = await load_mcp_tools(session)

    if logger:
        logger.debug(f"Loaded {len(tools)} tools")

    agent = create_agent(
        model=model,
        tools=tools,
        response_format=response_format,
        debug=debug,
    )

    if logger:
        logger.debug(f"Created agent with model={model}, debug={debug}")

    return agent


def create_aggregation_agent(
    *,
    model: str = "deepseek-chat",
    response_format: type = AggregationOutput,
) -> Any:
    """Create an aggregation agent without tools.

    The aggregation agent synthesizes extraction results into a comparison
    table and summary. It doesn't need browser tools, only structured output.

    Args:
        model: Model identifier (default: "deepseek-chat")
        response_format: Pydantic model for structured output (default: AggregationOutput)

    Returns:
        Configured agent ready for invocation

    Example:
        agent = create_aggregation_agent()
        response = await agent.ainvoke(aggregation_prompt)
    """
    agent = create_agent(
        model=model,
        tools=[],  # No tools needed for aggregation
        response_format=response_format,
    )

    return agent
