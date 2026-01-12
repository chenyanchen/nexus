"""Multi-phase news aggregator with extraction and aggregation pipeline.

Architecture:
- Planning phase: Selects relevant news sources
- Extraction phase: Scrapes articles from sources in parallel batches
- Aggregation phase: Synthesizes results into comparison table
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from langchain.agents import create_agent
from langchain.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from schemas import (
    AggregationOutput,
    ArticleExtraction,
    MediaComparison,
    NewsSource,
    PlanningOutput,
    SelectedSource,
    SourceProcessingResult,
)

# Global news sources list
GLOBAL_SOURCES: list[NewsSource] = [
    NewsSource(
        country="联合国", media_name="联合国新闻网", url="https://news.un.org/en/"
    ),
    NewsSource(country="美国", media_name="CNN", url="https://edition.cnn.com/"),
    NewsSource(country="美国", media_name="AP", url="https://www.ap.org/"),
    NewsSource(country="俄罗斯", media_name="RT", url="https://www.rt.com/"),
    NewsSource(country="俄罗斯", media_name="TASS", url="https://tass.com/"),
    NewsSource(country="德国", media_name="Die Zeit", url="https://www.zeit.de/index"),
    NewsSource(
        country="英国", media_name="Telegraph", url="https://www.telegraph.co.uk/"
    ),
    NewsSource(
        country="法国", media_name="France 24", url="https://www.france24.com/en/"
    ),
    NewsSource(country="日本", media_name="NHK", url="https://www3.nhk.or.jp/news/"),
    NewsSource(country="韩国", media_name="Yonhap", url="https://en.yna.co.kr/"),
    NewsSource(country="意大利", media_name="ANSA", url="https://www.ansa.it/english"),
    NewsSource(country="加拿大", media_name="CTV News", url="https://www.ctvnews.ca/"),
    NewsSource(
        country="巴西",
        media_name="Folha de S.Paulo",
        url="https://www.folha.uol.com.br/",
    ),
    NewsSource(
        country="以色列",
        media_name="Times of Israel",
        url="https://www.timesofisrael.com/",
    ),
    NewsSource(country="伊朗", media_name="Press TV", url="https://www.presstv.ir/"),
    NewsSource(
        country="新加坡", media_name="Mothership.SG", url="https://mothership.sg"
    ),
    NewsSource(
        country="乌克兰",
        media_name="Kyiv Independent",
        url="https://kyivindependent.com/",
    ),
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


planning_system_prompt = SystemMessage("""You are a media analysis expert selecting news sources.

Task: Select 10-12 most relevant news sources for the topic.

Selection criteria:
1. Geographic diversity (different regions/perspectives)
2. Political diversity (different political leanings)
3. Reliability (established mainstream sources)
4. Likely to have coverage of this topic

Return your selection as structured output following the PlanningOutput schema.""")

planning_human_prompt = HumanMessage("""Topic: {topic}

{sources}

Select 10-12 sources from the list above that will provide diverse perspectives on this topic.

For each selected source, assign a priority level:
- high: Major international outlets directly relevant to the topic
- medium: Regional outlets with valuable perspectives
- low: Backup sources for additional context""")

planning_chat_prompt_template = ChatPromptTemplate(
    messages=[planning_system_prompt, planning_human_prompt]
)

# Extraction phase prompts
extraction_system_prompt = SystemMessage("""You are a news extraction specialist.

Task: Visit the homepage and find news about the given topic.

Steps:
1. Navigate to the homepage
2. Look for headlines/articles about the topic
3. If found, click to read the article
4. Extract: headline, article URL, core viewpoint (1-2 sentences)
5. Return structured output

If no relevant news is found, return found_coverage=false.""")

extraction_human_prompt = HumanMessage("""Visit {url} and search for news about: {topic}

Only look at the homepage - don't navigate deep into the site.""")

extraction_chat_prompt_template = ChatPromptTemplate(
    messages=[extraction_system_prompt, extraction_human_prompt]
)

# Aggregation phase prompts
aggregation_system_prompt = SystemMessage("""You are a media analysis synthesizer.

Task: Aggregate extracted articles into a comparison table and summary.

Requirements:
1. Create comparison table sorted by relevance/importance
2. Write 2-3 sentence summary highlighting key patterns, differences, or consensus
3. Return structured output following AggregationOutput schema""")

aggregation_human_prompt = HumanMessage("""Topic: {topic}

Extracted articles from {source_count} sources:
{results_json}

Create final aggregation with comparison table and summary.""")

aggregation_chat_prompt_template = ChatPromptTemplate(
    messages=[aggregation_system_prompt, aggregation_human_prompt]
)


async def planning_phase(topic: str) -> PlanningOutput:
    """Phase 1: Select relevant sources without browser tools (no context bloat)."""
    print(f"\n=== PLANNING PHASE ===")
    print(f"Topic: {topic}")

    agent = create_agent(
        model="deepseek-chat",
        tools=[],  # No tools needed for planning
        response_format=PlanningOutput,
        debug=True,
    )

    sources_formatted = format_sources_for_planning(GLOBAL_SOURCES)
    response = await agent.ainvoke(
        planning_chat_prompt_template.invoke(
            {"topic": topic, "sources": sources_formatted}
        )
    )

    planning_output: PlanningOutput = response["structured_response"]
    print(f"Selected {len(planning_output.selected_sources)} sources")
    print(f"Rationale: {planning_output.rationale}")

    return planning_output


async def extract_from_source(
    source: SelectedSource, topic: str, session: ClientSession
) -> SourceProcessingResult:
    """Extraction phase: Process a single source with fresh agent context."""
    print(f"\n--- Processing: {source.media_name} ({source.country}) ---")

    try:
        tools = await load_mcp_tools(session)

        agent = create_agent(
            model="deepseek-chat",
            tools=tools,
            response_format=ArticleExtraction,
            debug=True,
        )

        response = await agent.ainvoke(
            extraction_chat_prompt_template.invoke({"url": source.url, "topic": topic})
        )

        # Get structured output
        article: ArticleExtraction = response["structured_response"]

        result = SourceProcessingResult(
            country=source.country,
            media_name=source.media_name,
            homepage_url=source.url,
            found_coverage=True,
            article=article,
        )

        print(f"✓ Found: {article.headline}")
        return result

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return SourceProcessingResult(
            country=source.country,
            media_name=source.media_name,
            homepage_url=source.url,
            found_coverage=False,
            error=str(e),
        )


async def extract_from_sources(
    sources: list[SelectedSource], topic: str
) -> list[SourceProcessingResult]:
    """Extraction phase: Process sources in small batches to manage resources."""
    print(f"\n=== EXTRACTION PHASE: Processing {len(sources)} sources ===")

    all_results = []

    # Process in batches of 3 to avoid too many concurrent browser instances
    batch_size = 3
    for i in range(0, len(sources), batch_size):
        batch = sources[i : i + batch_size]
        print(f"\nBatch {i // batch_size + 1}/{(len(sources) - 1) // batch_size + 1}")

        # Create fresh MCP session for each batch
        server_parameters = StdioServerParameters(
            command="npx",
            args=["@playwright/mcp@latest"],
        )

        async with stdio_client(server=server_parameters) as (reader, writer):
            async with ClientSession(
                read_stream=reader, write_stream=writer
            ) as session:
                await session.initialize()

                # Process batch sources concurrently
                tasks = [
                    extract_from_source(source, topic, session) for source in batch
                ]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Handle exceptions
                for idx, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        batch_results[idx] = SourceProcessingResult(
                            country=batch[idx].country,
                            media_name=batch[idx].media_name,
                            homepage_url=batch[idx].url,
                            found_coverage=False,
                            error=str(result),
                        )

                all_results.extend(batch_results)

        # Small delay between batches
        if i + batch_size < len(sources):
            await asyncio.sleep(2)

    successful = sum(1 for r in all_results if r.found_coverage)
    print(
        f"\n=== EXTRACTION PHASE COMPLETE: {successful}/{len(all_results)} sources found coverage ==="
    )

    return all_results


async def aggregate_results(
    topic: str, extraction_results: list[SourceProcessingResult]
) -> AggregationOutput:
    """Aggregation phase: Aggregate all results without browser tools (clean context)."""
    print(f"\n=== AGGREGATION PHASE: Aggregating results ===")

    # Filter to only successful extractions
    successful_results = [
        r for r in extraction_results if r.found_coverage and r.article
    ]

    # Convert to JSON for agent input (structured data only, no browser history)
    results_json = json.dumps(
        [r.model_dump() for r in successful_results],
        indent=2,
        ensure_ascii=False,
    )

    agent = create_agent(
        model="deepseek-chat",
        tools=[],  # No tools needed for aggregation
        response_format=AggregationOutput,
        debug=True,
    )

    response = await agent.ainvoke(
        aggregation_chat_prompt_template.invoke(
            {
                "topic": topic,
                "source_count": len(successful_results),
                "results_json": results_json,
            }
        )
    )

    aggregation: AggregationOutput = response["structured_response"]
    aggregation.topic = topic
    aggregation.total_sources_checked = len(extraction_results)
    aggregation.sources_with_coverage = len(successful_results)
    aggregation.processing_timestamp = datetime.now().isoformat()

    print(
        f"✓ Aggregation complete: {len(aggregation.comparison_table)} articles in table"
    )

    return aggregation


def save_output(output: AggregationOutput) -> Path:
    """Save aggregation output to markdown file."""
    output_dir = Path("runs")
    output_dir.mkdir(exist_ok=True)

    timestamp = int(datetime.now().timestamp())
    output_file = output_dir / f"report_{timestamp}.md"

    # Generate markdown
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
    print(f"\n✓ Report saved to: {output_file}")

    return output_file


async def main():
    """Main orchestration: Planning → Extraction → Aggregation."""
    topic = "委内瑞拉总统被美国逮捕"  # Venezuela president arrested by US

    # Phase 1: Planning (no browser tools, minimal context)
    planning_output = await planning_phase(topic)

    # Phase 2: Extraction (each source processed independently with fresh context)
    extraction_results = await extract_from_sources(
        planning_output.selected_sources, topic
    )

    # Phase 3: Aggregation (no browser tools, only structured data)
    final_output = await aggregate_results(topic, extraction_results)

    # Save output
    save_output(final_output)

    print("\n=== PIPELINE COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(main())
