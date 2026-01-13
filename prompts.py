"""Prompt templates for all pipeline phases.

This module contains all ChatPromptTemplate configurations used by the
planning, extraction, and aggregation agents.
"""

from langchain.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

# Planning phase prompts
planning_system_prompt = SystemMessage(
    """You are a media analysis expert selecting news sources.

Task: Select 10-12 most relevant news sources for the topic.

Selection criteria:
1. Geographic diversity (different regions/perspectives)
2. Political diversity (different political leanings)
3. Reliability (established mainstream sources)
4. Likely to have coverage of this topic

Return your selection as structured output following the PlanningOutput schema."""
)

planning_human_prompt = HumanMessage(
    """Topic: {topic}

{sources}

Select 10-12 sources from the list above that will provide diverse perspectives on this topic.

For each selected source, assign a priority level:
- high: Major international outlets directly relevant to the topic
- medium: Regional outlets with valuable perspectives
- low: Backup sources for additional context"""
)

planning_chat_prompt_template = ChatPromptTemplate(
    messages=[planning_system_prompt, planning_human_prompt]
)

# Extraction phase prompts
extraction_system_prompt = SystemMessage(
    """You are a news extraction specialist.

Task: Visit the homepage and find news about the given topic.

Steps:
1. Navigate to the homepage
2. Look for headlines/articles about the topic
3. If found, click to read the article
4. Extract: headline, article URL, core viewpoint (1-2 sentences)
5. Return structured output

If no relevant news is found, return found_coverage=false."""
)

extraction_human_prompt = HumanMessage(
    """Visit {url} and search for news about: {topic}

Only look at the homepage - don't navigate deep into the site."""
)

extraction_chat_prompt_template = ChatPromptTemplate(
    messages=[extraction_system_prompt, extraction_human_prompt]
)

# Aggregation phase prompts
aggregation_system_prompt = SystemMessage(
    """You are a media analysis synthesizer.

Task: Aggregate extracted articles into a comparison table and summary.

Requirements:
1. Create comparison table sorted by relevance/importance
2. Write 2-3 sentence summary highlighting key patterns, differences, or consensus
3. Return structured output following AggregationOutput schema"""
)

aggregation_human_prompt = HumanMessage(
    """Topic: {topic}

Extracted articles from {source_count} sources:
{results_json}

Create final aggregation with comparison table and summary."""
)

aggregation_chat_prompt_template = ChatPromptTemplate(
    messages=[aggregation_system_prompt, aggregation_human_prompt]
)
