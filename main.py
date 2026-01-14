"""Multi-phase news aggregator with extraction and aggregation pipeline.

Architecture:
- Planning phase: Selects relevant news sources
- Extraction phase: Scrapes articles from sources in parallel batches
- Aggregation phase: Synthesizes results into comparison table
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import ValidationError

from agents import (
    create_aggregation_agent,
    create_extraction_agent,
    create_planning_agent,
)
from extraction_core import (
    create_error_result,
    create_success_result,
    handle_extraction_error,
    validate_agent_response,
)
from logging_utils import (
    log_agent_call,
    log_batch_complete,
    log_batch_start,
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
    ArticleExtraction,
    MediaComparison,
    NewsSource,
    PlanningOutput,
    SelectedSource,
    SourceProcessingResult,
)

# fmt: off
# Global news sources list
GLOBAL_SOURCES: list[NewsSource] = [
    NewsSource(country="联合国", media_name="联合国新闻网", url="https://news.un.org/en/"),
    NewsSource(country="美国", media_name="CNN", url="https://edition.cnn.com/"),
    NewsSource(country="美国", media_name="AP", url="https://www.ap.org/"),
    NewsSource(country="俄罗斯", media_name="RT", url="https://www.rt.com/"),
    NewsSource(country="俄罗斯", media_name="TASS", url="https://tass.com/"),
    NewsSource(country="德国", media_name="Die Zeit", url="https://www.zeit.de/index"),
    NewsSource(country="英国", media_name="Telegraph", url="https://www.telegraph.co.uk/"),
    NewsSource(country="法国", media_name="France 24", url="https://www.france24.com/en/"),
    NewsSource(country="日本", media_name="NHK", url="https://www3.nhk.or.jp/news/"),
    NewsSource(country="韩国", media_name="Yonhap", url="https://en.yna.co.kr/"),
    NewsSource(country="意大利", media_name="ANSA", url="https://www.ansa.it/english"),
    NewsSource(country="加拿大", media_name="CTV News", url="https://www.ctvnews.ca/"),
    NewsSource(country="巴西", media_name="Folha de S.Paulo", url="https://www.folha.uol.com.br/"),
    NewsSource(country="以色列", media_name="Times of Israel", url="https://www.timesofisrael.com/"),
    NewsSource(country="伊朗", media_name="Press TV", url="https://www.presstv.ir/"),
    NewsSource(country="新加坡", media_name="Mothership.SG", url="https://mothership.sg"),
    NewsSource(country="乌克兰", media_name="Kyiv Independent", url="https://kyivindependent.com/"),
]


def format_sources_for_planning(sources: list[NewsSource]) -> str:
    """Format sources as a readable list grouped by country."""
    by_country: dict[str, list[NewsSource]] = {}
    for source in sources:
        by_country.setdefault(source.country, []).append(source)

    lines = ["Available news sources (grouped by country/organization):"]
    for country, country_sources in sorted(by_country.items()):
        lines.append(f"\n{country}:")
        for source in country_sources:
            lines.append(f"  - {source.media_name}: {source.url}")

    return "\n".join(lines)


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
        response = await agent.ainvoke(extraction_chat_prompt_template.invoke(input_data))

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
    """Extraction phase: Process sources in small batches to manage resources."""
    log_phase_start(
        logger,
        "extraction",
        {"total_sources": len(sources), "topic": topic},
    )

    all_results = []

    batch_size = 3
    total_batches = (len(sources) - 1) // batch_size + 1

    for i in range(0, len(sources), batch_size):
        batch = sources[i : i + batch_size]
        batch_num = i // batch_size + 1

        log_batch_start(
            logger,
            batch_num,
            total_batches,
            [s.media_name for s in batch],
        )

        async with create_mcp_session() as session:
            tasks = [
                extract_from_source(source, topic, session, logger, run_dir)
                for source in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    batch_results[idx] = SourceProcessingResult(
                        country=batch[idx].country,
                        media_name=batch[idx].media_name,
                        homepage_url=batch[idx].url,
                        found_coverage=False,
                        error=str(result),
                    )

            log_batch_complete(logger, batch_num, batch_results)

            all_results.extend(batch_results)

        if i + batch_size < len(sources):
            await asyncio.sleep(2)

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

    save_phase_output(run_dir, "extraction", "all_results", all_results)

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
        [r.model_dump() for r in successful_results],
        indent=2,
        ensure_ascii=False,
    )

    agent = create_aggregation_agent()

    input_data = {
        "topic": topic,
        "source_count": len(successful_results),
        "results_json": results_json,
    }
    response = await agent.ainvoke(
        aggregation_chat_prompt_template.invoke(input_data)
    )

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

| Country/Organization | Media Name | Article | Core Viewpoint |
| -------------------- | ---------- | ------- | -------------- |
"""

    for row in output.comparison_table:
        markdown += f"| {row.country} | {row.media_name} | [{row.article_title}]({row.article_url}) | {row.core_viewpoint} |\n"

    output_file.write_text(markdown, encoding="utf-8")

    logger.info(
        f"Report saved to {output_file}",
        extra={"output_file": str(output_file)},
    )

    return output_file


async def main():
    """Main orchestration: Planning → Extraction → Aggregation."""
    topic = "委内瑞拉总统被美国逮捕"

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger, run_dir = setup_phase_logging(run_id, "full_pipeline")

    logger.info(f"Starting pipeline for topic: {topic}", extra={"topic": topic})

    planning_output = await planning_phase(topic, logger, run_dir, num_sources=1)
    extraction_results = await extract_from_sources(
        planning_output.selected_sources, topic, logger, run_dir
    )
    final_output = await aggregate_results(topic, extraction_results, logger, run_dir)
    save_output(final_output, logger, run_dir)

    logger.info("Pipeline complete", extra={"run_id": run_id})


if __name__ == "__main__":
    asyncio.run(main())
