# Architecture: Map-Reduce with Structured Output

## The Difference: Map-Reduce vs Separate Agents

These are **complementary concepts**, not alternatives:

### Map-Reduce Pattern (Data Processing)
**What it solves**: Processing multiple independent inputs without context accumulation

```
┌─────────────────────────────────────────────────────────────┐
│                      MAP-REDUCE PATTERN                      │
└─────────────────────────────────────────────────────────────┘

Input: 50 news sources

EXTRACTION PHASE (Map Pattern - parallel, independent contexts):
  Source 1  →  [Agent] → Result 1  ┐
  Source 2  →  [Agent] → Result 2  │
  Source 3  →  [Agent] → Result 3  ├─→ [Results Array]
  ...                               │
  Source 50 →  [Agent] → Result 50 ┘

AGGREGATION PHASE (Reduce Pattern - single context, structured data only):
  [Results Array] → [Aggregator] → Final Table

✓ Each extraction agent has fresh context (20-50KB)
✓ Aggregation agent only sees structured JSON (30KB)
✓ Peak context never exceeds 100KB
```

### Separate Agents (Agent Specialization)
**What it solves**: Different phases need different capabilities

```
┌─────────────────────────────────────────────────────────────┐
│                     SEPARATE AGENTS                          │
└─────────────────────────────────────────────────────────────┘

Phase 1: PLANNING AGENT
  Tools: None (no browser)
  Input: Source list
  Output: PlanningOutput (selected sources)
  Context: ~10KB

Phase 2: EXECUTION AGENTS (Extraction Phase)
  Tools: Playwright (browser automation)
  Input: Single source URL + topic
  Output: SourceProcessingResult (structured)
  Context: ~20-50KB per instance

Phase 3: AGGREGATION AGENT (Aggregation Phase)
  Tools: None (no browser)
  Input: Array of SourceProcessingResult
  Output: AggregationOutput (final table)
  Context: ~30KB

✓ Planning agent doesn't waste tokens on browser tools
✓ Execution agents don't carry planning context
✓ Aggregation agent doesn't carry browser history
```

## Combined Implementation

Our solution uses **separate specialized agents** to implement the **map-reduce pattern**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    NEXUS PIPELINE                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 1: PLANNING                                           │
│ Agent Type: Planning Agent (no tools)                       │
│ Pattern: Single execution                                   │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
           PlanningOutput (10-12 sources)
                        │
┌───────────────────────┴──────────────────────────────────────┐
│ Phase 2: EXTRACTION                                          │
│ Agent Type: Execution Agents (with Playwright)              │
│ Pattern: Parallel processing with batching                  │
└──────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
   [CNN Agent]          [RT Agent]          [BBC Agent]
   Fresh context        Fresh context       Fresh context
         │                    │                    │
         ▼                    ▼                    ▼
   SourceResult1        SourceResult2       SourceResult3
         │                    │                    │
         └────────────────────┴────────────────────┘
                              │
                              ▼
                 [SourceResult1, SourceResult2, ...]
                              │
┌─────────────────────────────┴────────────────────────────────┐
│ Phase 3: AGGREGATION                                         │
│ Agent Type: Aggregation Agent (no tools)                     │
│ Pattern: Single execution with structured data only          │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
                     AggregationOutput
                              │
                              ▼
                      report_XXXXX.md
```

## Structured Output Flow

Every agent returns Pydantic models for type safety:

```python
# Phase 1: Planning
PlanningOutput = {
    "topic": str,
    "selected_sources": [SelectedSource, ...],
    "rationale": str
}

# Phase 2: Extraction (per source)
SourceProcessingResult = {
    "country": str,
    "media_name": str,
    "found_coverage": bool,
    "article": ArticleExtraction | None,  # ← Nested structured output
    "error": str | None
}

ArticleExtraction = {
    "headline": str,
    "article_url": str,
    "core_viewpoint": str,
    "publication_date": str | None
}

# Phase 3: Aggregation
AggregationOutput = {
    "topic": str,
    "total_sources_checked": int,
    "sources_with_coverage": int,
    "comparison_table": [MediaComparison, ...],
    "summary": str,
    "processing_timestamp": str
}
```

## Context Budget Breakdown

| Phase | Agent Type | Context Size | Why It's Small |
|-------|-----------|--------------|----------------|
| Planning | Planning Agent | ~10KB | Only source list → selection |
| Extraction (each) | Execution Agent | 20-50KB | Single site, fresh context per source |
| Aggregation | Aggregation Agent | ~30KB | Only structured JSON, no HTML/screenshots |

**Total Peak Context**: <100KB (78% under the 128K limit)

## Key Design Principles

1. **Isolation**: Each extraction execution is independent (no shared state)
2. **Specialization**: Agents only have tools they need for their phase
3. **Structure**: All outputs are Pydantic models (no free-form text)
4. **Batching**: Process 3 sources at a time (resource management)
5. **Fresh Context**: New agent instance per source (no history accumulation)

## When to Use This Pattern

Use this extraction/aggregation pattern with separate agents when:
- ✓ Processing many independent data sources (N > 5)
- ✓ Each source has complex processing (browser automation, API calls)
- ✓ Context limits are a concern (128K for DeepSeek)
- ✓ Different phases need different tools

Don't use this pattern when:
- ✗ Single source or very few sources (< 3)
- ✗ Sources must be processed sequentially with shared state
- ✗ Real-time streaming required (this is batch processing)
