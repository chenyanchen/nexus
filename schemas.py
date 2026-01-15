"""Structured output schemas for all agents in news aggregator pipeline."""

from pydantic import BaseModel, Field, HttpUrl, field_validator

# Schema validation constants
MIN_PLANNING_SOURCES = 1
MAX_PLANNING_SOURCES = 15
MIN_HEADLINE_LENGTH = 5
MAX_HEADLINE_LENGTH = 500
MIN_VIEWPOINT_LENGTH = 20
MAX_VIEWPOINT_LENGTH = 1000
MIN_VIEWPOINT_WORDS = 10


class SelectedSource(BaseModel):
    """A news source selected for processing."""

    country: str = Field(
        description="Country or organization (e.g., 'United States', 'United Nations')"
    )
    media_name: str = Field(description="Name of the media outlet")
    url: str = Field(description="URL to visit")


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
        min_length=MIN_PLANNING_SOURCES,
        max_length=MAX_PLANNING_SOURCES,
    )
    rationale: str = Field(
        description="Brief explanation of selection criteria (max 2 sentences)"
    )


class ArticleExtraction(BaseModel):
    """Extracted information from a single news article."""

    headline: str = Field(
        description="Article headline or title",
        min_length=MIN_HEADLINE_LENGTH,
        max_length=MAX_HEADLINE_LENGTH,
    )
    article_url: HttpUrl = Field(
        description="Direct URL to the article (must be valid HTTP/HTTPS URL)"
    )
    core_viewpoint: str = Field(
        description="The media's core viewpoint in 1-2 sentences, focusing on their perspective or stance",
        min_length=MIN_VIEWPOINT_LENGTH,
        max_length=MAX_VIEWPOINT_LENGTH,
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
        """Ensure viewpoint contains meaningful content."""
        word_count = len(v.split())
        if word_count < MIN_VIEWPOINT_WORDS:
            raise ValueError(
                f"Core viewpoint too short ({word_count} words). Need at least {MIN_VIEWPOINT_WORDS} words for meaningful analysis."
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
