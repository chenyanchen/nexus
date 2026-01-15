"""Multi-phase news aggregator with extraction and aggregation pipeline.

Architecture:
- Planning phase: Selects relevant news sources
- Extraction phase: Scrapes articles from sources sequentially
- Aggregation phase: Synthesizes results into comparison table
"""

import argparse
import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from mcp import ClientSession
from pydantic import ValidationError

from agents import (
    create_aggregation_agent,
    create_extraction_agent,
    create_planning_agent,
)
from extraction_core import (
    create_success_result,
    handle_extraction_error,
    validate_agent_response,
)
from logging_utils import (
    log_agent_call,
    log_phase_complete,
    log_phase_start,
    save_phase_output,
    setup_phase_logging,
)
from mcp_session import create_mcp_session
from prompts import (
    planning_chat_prompt_template,
    extraction_chat_prompt_template,
    aggregation_chat_prompt_template,
)
from schemas import (
    AggregationOutput,
    PlanningOutput,
    SelectedSource,
    SourceProcessingResult,
)
from sources import GLOBAL_SOURCES, format_sources_for_planning

# Pipeline configuration constants
DEFAULT_NUM_SOURCES = 10


async def planning_phase(
    topic: str,
    logger: logging.Logger,
    run_dir: Path,
    num_sources: int = 1,
) -> PlanningOutput:
    """Phase 1: Select relevant sources without browser tools (no context bloat)."""
    start_time = time.time()

    log_phase_start(logger, "planning", {"topic": topic, "num_sources": num_sources})

    agent = create_planning_agent()

    sources_formatted = format_sources_for_planning(GLOBAL_SOURCES)
    input_data = {
        "topic": topic,
        "sources": sources_formatted,
        "num_sources": num_sources,
    }
    response = await agent.ainvoke(planning_chat_prompt_template.invoke(input_data))

    planning_output: PlanningOutput = response["structured_response"]
    duration_ms = (time.time() - start_time) * 1000

    log_agent_call(
        logger,
        "planning",
        None,
        input_data,
        response,
        None,
        duration_ms,
    )

    log_phase_complete(
        logger,
        "planning",
        {
            "sources_selected": len(planning_output.selected_sources),
            "rationale": planning_output.rationale,
        },
    )

    save_phase_output(run_dir, "planning", "output", planning_output)

    return planning_output


async def extract_from_source(
    source: SelectedSource,
    topic: str,
    session: ClientSession,
    logger: logging.Logger,
    run_dir: Path,
) -> SourceProcessingResult:
    """Extraction phase: Process a single source with fresh agent context."""
    start_time = time.time()
    response = None

    logger.info(
        f"Processing {source.media_name}",
        extra={
            "source": source.media_name,
            "country": source.country,
            "url": source.url,
        },
    )

    try:
        agent = await create_extraction_agent(session)

        input_data = {"url": source.url, "topic": topic}
        response = await agent.ainvoke(
            extraction_chat_prompt_template.invoke(input_data)
        )

        article = validate_agent_response(response, source, logger)

        return create_success_result(
            source, article, response, topic, start_time, logger, run_dir
        )

    except (KeyError, ValidationError, Exception) as e:
        return handle_extraction_error(
            e, source, topic, start_time, logger, run_dir, response
        )


async def extract_from_sources(
    sources: list[SelectedSource],
    topic: str,
    logger: logging.Logger,
    run_dir: Path,
) -> list[SourceProcessingResult]:
    """Extraction phase: Process sources sequentially.

    Uses a single MCP session to avoid expensive server restarts.
    Sources are processed one at a time because Playwright operates on a single page.
    """
    log_phase_start(
        logger,
        "extraction",
        {"total_sources": len(sources), "topic": topic},
    )

    all_results: list[SourceProcessingResult] = []

    # Process sources sequentially - MCP Playwright operates on single page
    async with create_mcp_session() as session:
        for i, source in enumerate(sources):
            logger.info(
                f"Processing source {i + 1}/{len(sources)}",
                extra={
                    "source": source.media_name,
                    "progress": f"{i + 1}/{len(sources)}",
                },
            )
            result = await extract_from_source(source, topic, session, logger, run_dir)
            all_results.append(result)

    successful = sum(1 for r in all_results if r.found_coverage)

    log_phase_complete(
        logger,
        "extraction",
        {
            "total_sources": len(all_results),
            "successful": successful,
            "failed": len(all_results) - successful,
        },
    )

    save_phase_output(run_dir, "extraction", "output", all_results)

    return all_results


async def aggregate_results(
    topic: str,
    extraction_results: list[SourceProcessingResult],
    logger: logging.Logger,
    run_dir: Path,
) -> AggregationOutput:
    """Aggregation phase: Aggregate all results without browser tools (clean context)."""
    start_time = time.time()

    log_phase_start(
        logger,
        "aggregation",
        {
            "topic": topic,
            "extraction_count": len(extraction_results),
        },
    )

    successful_results = [
        r for r in extraction_results if r.found_coverage and r.article
    ]

    results_json = json.dumps(
        [r.model_dump(mode="json") for r in successful_results],
        indent=2,
        ensure_ascii=False,
    )

    agent = create_aggregation_agent()

    input_data = {
        "topic": topic,
        "source_count": len(successful_results),
        "results_json": results_json,
    }
    response = await agent.ainvoke(aggregation_chat_prompt_template.invoke(input_data))

    aggregation: AggregationOutput = response["structured_response"]
    aggregation.topic = topic
    aggregation.total_sources_checked = len(extraction_results)
    aggregation.sources_with_coverage = len(successful_results)
    aggregation.processing_timestamp = datetime.now().isoformat()

    duration_ms = (time.time() - start_time) * 1000

    log_agent_call(
        logger,
        "aggregation",
        None,
        input_data,
        response,
        None,
        duration_ms,
    )

    log_phase_complete(
        logger,
        "aggregation",
        {
            "articles_in_table": len(aggregation.comparison_table),
            "summary_length": len(aggregation.summary),
        },
    )

    save_phase_output(run_dir, "aggregation", "output", aggregation)

    return aggregation


def save_output(
    output: AggregationOutput, logger: logging.Logger, run_dir: Path
) -> Path:
    """Save aggregation output to markdown file."""
    output_file = run_dir / "report.md"

    markdown = f"""# News Aggregation Report: {output.topic}

**Generated:** {output.processing_timestamp}
**Sources Checked:** {output.total_sources_checked}
**Sources with Coverage:** {output.sources_with_coverage}

## Summary

{output.summary}

## Media Comparison Table

| Country/Organization | Media Name | Article | Sentiment | Core Viewpoint |
| -------------------- | ---------- | ------- | --------- | -------------- |
"""

    for row in output.comparison_table:
        markdown += f"| {row.country} | {row.media_name} | [{row.article_title}]({row.article_url}) | {row.sentiment} | {row.core_viewpoint} |\n"

    output_file.write_text(markdown, encoding="utf-8")

    logger.info(
        f"Report saved to {output_file}",
        extra={"output_file": str(output_file)},
    )

    return output_file


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="AI-powered news aggregator that synthesizes multi-source reporting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --topic "Climate change summit"
  python main.py -t "US election" -n 5

Environment variables:
  DEEPSEEK_API_KEY  Required. API key for DeepSeek LLM
        """,
    )
    parser.add_argument(
        "--topic",
        "-t",
        required=True,
        help="News topic to search for",
    )
    parser.add_argument(
        "--num-sources",
        "-n",
        type=int,
        default=DEFAULT_NUM_SOURCES,
        help=f"Number of sources to process (default: {DEFAULT_NUM_SOURCES})",
    )
    return parser.parse_args()


async def main():
    """Main orchestration: Planning → Extraction → Aggregation."""
    args = parse_args()
    topic = args.topic
    num_sources = args.num_sources

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger, run_dir = setup_phase_logging(run_id, "pipeline")

    logger.info(
        "Starting pipeline",
        extra={"topic": topic, "num_sources": num_sources},
    )

    planning_output = await planning_phase(
        topic, logger, run_dir, num_sources=num_sources
    )
    extraction_results = await extract_from_sources(
        planning_output.selected_sources, topic, logger, run_dir
    )
    final_output = await aggregate_results(topic, extraction_results, logger, run_dir)
    save_output(final_output, logger, run_dir)

    logger.info("Pipeline complete", extra={"run_id": run_id})


if __name__ == "__main__":
    asyncio.run(main())
