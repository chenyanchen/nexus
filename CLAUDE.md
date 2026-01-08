# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nexus is an AI-driven news aggregator that orchestrates LLMs to ingest, cross-reference, and synthesize multi-source reporting into structured, unbiased event summaries. The system prevents cognitive bias by autonomously gathering diverse viewpoints from global news sources.

## Architecture

### Core Components

- **main.py**: Legacy single-agent implementation (context issues with many sources)
- **main_mapreduce.py**: Production implementation using map-reduce pattern to avoid context overflow
- **schemas.py**: Pydantic models for structured output across all agent phases

### Map-Reduce Pipeline (main_mapreduce.py)

The pipeline uses **three separate specialized agents** to implement the map-reduce pattern:

1. **Planning Agent** (no tools)
   - Selects 10-12 most relevant sources from available list
   - Returns `PlanningOutput` with structured source selections
   - Minimal context: only source list in, selection list out

2. **Execution Agents** (with Playwright tools) - MAP PHASE
   - Each source processed by independent agent instance
   - Fresh context per source (previous browsing history not retained)
   - Returns `SourceProcessingResult` with structured article extraction
   - Batched execution (3 sources per batch) to manage resources

3. **Aggregation Agent** (no tools) - REDUCE PHASE
   - Receives only structured data from map phase (no browser history)
   - Synthesizes comparison table and summary
   - Returns `AggregationOutput` with final markdown-ready data

**Context Management Strategy:**
- Planning phase: ~10KB (source list only)
- Each map execution: ~20-50KB (single site, fresh context)
- Reduce phase: ~30KB (structured JSON only, no HTML/screenshots)
- Total peak context: <100KB (well under 128K limit)

### Technology Stack

- **LangChain**: Agent orchestration framework
- **MCP (Model Context Protocol)**: Tool integration layer connecting LLM to external capabilities
- **Playwright MCP Server**: Provides browser automation tools via `npx @playwright/mcp@latest`
- **DeepSeek**: LLM model for agent reasoning and text generation
- **Python 3.12**: Required runtime version

### Key Dependencies

- `langchain>=1.2.0`: Agent framework
- `langchain-deepseek>=1.0.1`: DeepSeek model integration
- `langchain-mcp-adapters>=0.2.1`: Bridges MCP tools to LangChain
- Node.js + npx: Required for Playwright MCP server

## Development Commands

### Environment Setup

```bash
# Install dependencies (recommended method)
uv sync
```

### Running the Application

```bash
# Run the map-reduce pipeline (recommended)
python main_mapreduce.py

# Run legacy single-agent version (may exceed context limit)
python main.py
```

**Prerequisites**: Node.js must be installed and available in PATH for `npx @playwright/mcp@latest` to work.

### Configuration

- Environment variables should be used for API keys and credentials (e.g., DEEPSEEK_API_KEY)
- Edit `topic` variable in `main_mapreduce.py` to analyze different news events
- Modify `GLOBAL_SOURCES` list to add/remove news sources
- Adjust `batch_size` in `map_phase_batch()` based on your system resources (default: 3)

## Code Style

- Python 3.12 with 4-space indentation (PEP 8)
- `snake_case` for functions/variables, `CamelCase` for classes
- Prefer small, focused async functions when extending agent capabilities
- Commit messages follow conventional style: `feat:`, `fix:`, etc.

## Output Structure

- `outputs/`: General artifacts directory
- `news_aggregator_output/`: Contains generated markdown reports with timestamps (e.g., `report_1767847709.md`)
- Output format: Markdown tables comparing country/organization, media source, article links, and core viewpoints

## Important Notes

- **Structured output required**: All agents must return Pydantic models defined in `schemas.py`
- **Async-first architecture**: All MCP client operations and agent invocations use async/await
- **MCP stdio protocol**: Agents communicate with Playwright server via standard input/output streams
- **Context management**: Map-reduce pattern ensures no single agent accumulates >100KB context
- **Fresh context per source**: Each news source processed with independent agent instance
- **Batched processing**: Default 3 concurrent sources per batch to manage browser resources
- **Network dependency**: Requires internet access for both Playwright operations and accessing news sources
- **No test suite**: Testing infrastructure not yet configured

## Structured Output Schemas

All agents use Pydantic models for type safety and validation:

- `PlanningOutput`: Planning agent returns selected sources
- `SourceProcessingResult`: Map phase returns per-source extraction
- `ArticleExtraction`: Nested schema for article details
- `AggregationOutput`: Reduce phase returns final comparison table
- `MediaComparison`: Individual table rows

When modifying agent prompts, always specify `config={"response_format": SchemaClass}` to enforce structured output.

## Future Extension Points

When adding new functionality:
- Keep MCP client initialization logic in separate async functions
- Add new tool integrations through MCP adapters rather than direct imports
- Consider breaking down large prompts into configurable templates
- Output handlers should write to `outputs/` or `news_aggregator_output/` directories
