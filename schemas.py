"""Structured output schemas for all agents in the news aggregator pipeline."""

from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator


class SelectedSource(BaseModel):
    """A news source selected for processing."""

    country: str = Field(
        description="Country or organization (e.g., 'United States', 'United Nations')"
    )
    media_name: str = Field(description="Name of the media outlet")
    url: str = Field(description="URL to visit")
    priority: Literal["high", "medium", "low"] = Field(
        description="Priority based on relevance to the topic"
    )


class NewsSource(BaseModel):
    """A news source available in the global catalog."""

    country: str = Field(
        description="Country or organization (e.g., 'United States', 'United Nations')"
    )
    media_name: str = Field(description="Name of the media outlet")
    url: str = Field(description="Official homepage URL")


class PlanningOutput(BaseModel):
    """Output from the planning agent that selects relevant sources."""

    topic: str = Field(description="The news topic being researched")
    selected_sources: list[SelectedSource] = Field(
        description="List of selected news sources to process",
        min_length=1,
        max_length=15,
    )
    rationale: str = Field(
        description="Brief explanation of selection criteria (max 2 sentences)"
    )


class ArticleExtraction(BaseModel):
    """Extracted information from a single news article."""

    headline: str = Field(
        description="Article headline or title", min_length=5, max_length=500
    )
    article_url: HttpUrl = Field(
        description="Direct URL to the article (must be valid HTTP/HTTPS URL)"
    )
    core_viewpoint: str = Field(
        description="The media's core viewpoint in 1-2 sentences, focusing on their perspective or stance",
        min_length=20,
        max_length=1000,
    )
    publication_date: str | None = Field(
        default=None, description="Publication date if available (YYYY-MM-DD format)"
    )

    @field_validator("headline", "core_viewpoint")
    @classmethod
    def reject_empty_and_placeholders(cls, v: str, info) -> str:
        """Ensure fields are not empty or placeholder text."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty or whitespace")

        stripped = v.strip()
        placeholders = ["n/a", "none", "undefined", "null", ""]
        if stripped.lower() in placeholders:
            raise ValueError(
                f"{info.field_name} cannot be placeholder text like '{stripped}'"
            )

        return stripped

    @field_validator("core_viewpoint")
    @classmethod
    def validate_viewpoint_length(cls, v: str) -> str:
        """Ensure viewpoint contains meaningful content (at least 10 words)."""
        word_count = len(v.split())
        if word_count < 10:
            raise ValueError(
                f"Core viewpoint too short ({word_count} words). Need at least 10 words for meaningful analysis."
            )
        return v


class SourceProcessingResult(BaseModel):
    """Result from processing a single news source (extraction phase output)."""

    country: str
    media_name: str
    homepage_url: str
    found_coverage: bool = Field(description="Whether relevant news was found")
    article: ArticleExtraction | None = Field(
        default=None, description="Extracted article if coverage was found"
    )
    error: str | None = Field(
        default=None, description="Error message if processing failed"
    )


class MediaComparison(BaseModel):
    """A row in the final comparison table."""

    country: str
    media_name: str
    article_title: str
    article_url: str
    core_viewpoint: str


class AggregationOutput(BaseModel):
    """Final aggregated output (aggregation phase output)."""

    topic: str
    total_sources_checked: int
    sources_with_coverage: int
    comparison_table: list[MediaComparison] = Field(
        description="Rows for the comparison table, sorted by priority/relevance"
    )
    summary: str = Field(
        description="2-3 sentence summary highlighting key patterns or disagreements across sources"
    )
    processing_timestamp: str = Field(description="ISO 8601 timestamp")
