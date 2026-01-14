# CLAUDE.md

This file provides technical guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Workflow

1. **Make changes**: Edit code files as needed
2. **Check syntax**: Run `uv run python -m py_compile main.py <file>` to verify syntax
3. **Run tests**: Execute test suite (Note: Testing infrastructure not yet configured)
4. **Lint before commit**: Format code with `uv run ruff format`
5. **Commit**: Write conventional commit message (`feat:`, `fix:`, etc.) and commit changes

## Architecture

### Core Components

- **main.py**: Production implementation using map-reduce pattern (extraction and aggregation) to avoid context overflow
- **schemas.py**: Pydantic models for structured output across all agent phases

### Pipeline Architecture (Extraction and Aggregation)

The pipeline uses **three separate specialized agents** to implement the map-reduce pattern:

1. **Planning Agent** (no tools)

   - Selects 10-12 most relevant sources from available list
   - Returns `PlanningOutput` with structured source selections
   - Minimal context: only source list in, selection list out

2. **Execution Agents** (with Playwright tools) - EXTRACTION PHASE (map pattern)

   - Each source processed by independent agent instance
   - Fresh context per source (previous browsing history not retained)
   - Returns `SourceProcessingResult` with structured article extraction
   - Batched execution (3 sources per batch) to manage resources

3. **Aggregation Agent** (no tools) - AGGREGATION PHASE (reduce pattern)
   - Receives only structured data from extraction phase (no browser history)
   - Synthesizes comparison table and summary
   - Returns `AggregationOutput` with final markdown-ready data

**Context Management Strategy:**

- Planning phase: ~10KB (source list only)
- Each extraction execution: ~20-50KB (single site, fresh context)
- Aggregation phase: ~30KB (structured JSON only, no HTML/screenshots)
- Total peak context: <100KB (well under 128K limit)

### Technology Stack

- **LangChain**: Agent orchestration framework
- **MCP (Model Context Protocol)**: Tool integration layer connecting LLM to external capabilities
- **Playwright MCP Server**: Provides browser automation tools via `npx @playwright/mcp@latest`
- **DeepSeek**: LLM model for agent reasoning and text generation
- **Python 3.12**: Required runtime version

## Code Style

- Python 3.12 with 4-space indentation (PEP 8)
- `snake_case` for functions/variables, `CamelCase` for classes
- Prefer small, focused async functions when extending agent capabilities
- Commit messages follow conventional style: `feat:`, `fix:`, etc.

## Important Notes

- **Structured output required**: All agents must return Pydantic models defined in `schemas.py`
- **Async-first architecture**: All MCP client operations and agent invocations use async/await
- **MCP stdio protocol**: Agents communicate with Playwright server via standard input/output streams
- **Context management**: Extraction/aggregation pattern ensures no single agent accumulates >100KB context
- **Fresh context per source**: Each news source processed with independent agent instance
- **Batched processing**: Default 3 concurrent sources per batch to manage browser resources
- **Network dependency**: Requires internet access for both Playwright operations and accessing news sources
- **No test suite**: Testing infrastructure not yet configured

## Structured Output Schemas

All agents use Pydantic models for type safety and validation:

- `PlanningOutput`: Planning agent returns selected sources
- `SourceProcessingResult`: Extraction phase returns per-source extraction
- `ArticleExtraction`: Nested schema for article details
- `AggregationOutput`: Aggregation phase returns final comparison table
- `MediaComparison`: Individual table rows

When modifying agent prompts, always specify `config={"response_format": SchemaClass}` to enforce structured output.

## Future Extension Points

When adding new functionality:

- Keep MCP client initialization logic in separate async functions
- Add new tool integrations through MCP adapters rather than direct imports
- Consider breaking down large prompts into configurable templates
- Output handlers should write to `runs/`
