# Nexus

Nexus is an AI-driven news aggregator that orchestrates LLMs to ingest, cross-reference, and synthesize multi-source reporting into structured, unbiased event summaries. The system prevents cognitive bias by autonomously gathering diverse viewpoints from global news sources.

## Features

- Multi-source news aggregation from global outlets
- AI-powered cross-referencing and synthesis
- Structured, unbiased event summaries
- Context-aware extraction using map-reduce pattern
- Automated comparison tables across different viewpoints

## Prerequisites

- **Python 3.12+**: Required runtime version
- **Node.js**: Must be installed and available in PATH for `npx @playwright/mcp@latest` to work
- **DeepSeek API Key**: Required for LLM operations

## Installation

1. Clone the repository
2. Install dependencies with `uv`:

   ```bash
   uv sync
   ```

3. Set up environment variables:

   ```bash
   export DEEPSEEK_API_KEY=your_api_key_here
   ```

## Configuration

- **API Keys**: Set `DEEPSEEK_API_KEY` environment variable
- **Topic**: Edit `topic` variable in `main.py` to analyze different news events
- **News Sources**: Modify `GLOBAL_SOURCES` list in `main.py` to add/remove sources
- **Batch Size**: Adjust `batch_size` in `extract_from_sources()` based on system resources (default: 3)

## Usage

Run the news aggregator:

```bash
python main.py
```

The system will:

1. Select 10-12 most relevant news sources for your topic
2. Extract articles from each source using browser automation
3. Aggregate and synthesize viewpoints into a comparison table
4. Generate a markdown report with structured summaries

## Output

Generated reports are saved in the `news_aggregator_output/` directory with timestamps (e.g., `report_1767847709.md`).

Output format includes:

- Markdown tables comparing different sources
- Country/organization context
- Media source links
- Core viewpoints and perspectives
- Synthesis of common themes and differences

## Contributing

See [CLAUDE.md](CLAUDE.md) for technical architecture details and development guidelines when working with Claude Code.

## License

See LICENSE file for details.
