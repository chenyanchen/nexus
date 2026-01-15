"""Tests for Pydantic schema validation.

These tests verify that schemas properly validate data and reject invalid inputs.
"""

import pytest
from pydantic import ValidationError

from schemas import (
    ArticleExtraction,
    SourceProcessingResult,
    SelectedSource,
    PlanningOutput,
    MediaComparison,
    AggregationOutput,
)


class TestArticleExtraction:
    """Test ArticleExtraction schema validation."""

    def test_valid_article_with_all_fields(self):
        """Valid article data with all fields should pass validation."""
        article = ArticleExtraction(
            headline="Venezuela President Faces International Pressure",
            article_url="https://example.com/venezuela-crisis",
            core_viewpoint="The article discusses the international response to Venezuela's political crisis, emphasizing diplomatic solutions and economic sanctions.",
            publication_date="2026-01-12",
        )

        assert article.headline == "Venezuela President Faces International Pressure"
        assert str(article.article_url) == "https://example.com/venezuela-crisis"
        assert "international response" in article.core_viewpoint
        assert article.publication_date == "2026-01-12"

    def test_valid_article_without_publication_date(self):
        """Valid article without publication date should pass."""
        article = ArticleExtraction(
            headline="Venezuela President Faces International Pressure",
            article_url="https://example.com/venezuela-crisis",
            core_viewpoint="The article discusses the international response to Venezuela's political crisis, emphasizing diplomatic solutions.",
        )

        assert article.publication_date is None

    def test_empty_headline_should_fail(self):
        """Empty headline should raise ValidationError."""
        # This test WILL FAIL initially because current schema allows empty strings
        with pytest.raises(ValidationError, match="headline"):
            ArticleExtraction(
                headline="",
                article_url="https://example.com/article",
                core_viewpoint="This is a valid core viewpoint with more than ten words total in the sentence.",
            )

    def test_very_short_headline_should_fail(self):
        """Headline shorter than 5 characters should fail."""
        # This test WILL FAIL initially
        with pytest.raises(ValidationError, match="headline"):
            ArticleExtraction(
                headline="Hi",
                article_url="https://example.com/article",
                core_viewpoint="This is a valid core viewpoint with more than ten words total in the sentence.",
            )

    def test_invalid_url_format_should_fail(self):
        """Invalid URL format should raise ValidationError."""
        # This test WILL FAIL initially because current schema uses str, not HttpUrl
        with pytest.raises(ValidationError, match="url"):
            ArticleExtraction(
                headline="Valid headline here that is long enough",
                article_url="not-a-valid-url",
                core_viewpoint="This is a valid core viewpoint with more than ten words total in the sentence.",
            )

    def test_relative_url_should_fail(self):
        """Relative URL without scheme should fail."""
        # This test WILL FAIL initially
        with pytest.raises(ValidationError, match="url"):
            ArticleExtraction(
                headline="Valid headline here that is long enough",
                article_url="/article/123",
                core_viewpoint="This is a valid core viewpoint with more than ten words total in the sentence.",
            )

    def test_empty_core_viewpoint_should_fail(self):
        """Empty core_viewpoint should raise ValidationError."""
        # This test WILL FAIL initially
        with pytest.raises(ValidationError, match="core_viewpoint"):
            ArticleExtraction(
                headline="Valid headline here that is long enough",
                article_url="https://example.com/article",
                core_viewpoint="",
            )

    def test_very_short_viewpoint_should_fail(self):
        """Core viewpoint with fewer than 10 words should fail."""
        # This test WILL FAIL initially
        with pytest.raises(ValidationError, match="core_viewpoint|viewpoint"):
            ArticleExtraction(
                headline="Valid headline here that is long enough",
                article_url="https://example.com/article",
                core_viewpoint="Too short",
            )

    def test_placeholder_headline_should_fail(self):
        """Common placeholder text in headline should be rejected."""
        # This test WILL FAIL initially
        placeholders = ["N/A", "None", "undefined", "null"]

        for placeholder in placeholders:
            with pytest.raises(ValidationError, match="headline"):
                ArticleExtraction(
                    headline=placeholder,
                    article_url="https://example.com/article",
                    core_viewpoint="This is a valid core viewpoint with more than ten words total in the sentence.",
                )

    def test_placeholder_viewpoint_should_fail(self):
        """Common placeholder text in viewpoint should be rejected."""
        # This test WILL FAIL initially
        placeholders = ["N/A", "None", "undefined", "null"]

        for placeholder in placeholders:
            with pytest.raises(ValidationError, match="viewpoint"):
                ArticleExtraction(
                    headline="Valid headline here that is long enough",
                    article_url="https://example.com/article",
                    core_viewpoint=placeholder,
                )

    def test_whitespace_only_fields_should_fail(self):
        """Fields with only whitespace should be rejected."""
        # This test WILL FAIL initially
        with pytest.raises(ValidationError):
            ArticleExtraction(
                headline="   ",
                article_url="https://example.com/article",
                core_viewpoint="This is a valid core viewpoint with more than ten words total in the sentence.",
            )


class TestSourceProcessingResult:
    """Test SourceProcessingResult schema."""

    def test_successful_extraction_result(self):
        """Valid successful extraction result should pass."""
        article = ArticleExtraction(
            headline="Test Article Headline Here",
            article_url="https://example.com/article",
            core_viewpoint="This article presents a comprehensive analysis of the topic with multiple expert perspectives included.",
        )

        result = SourceProcessingResult(
            country="United States",
            media_name="Test News",
            homepage_url="https://example.com",
            found_coverage=True,
            article=article,
        )

        assert result.found_coverage is True
        assert result.article is not None
        assert result.error is None

    def test_failed_extraction_result(self):
        """Failed extraction with error message should pass."""
        result = SourceProcessingResult(
            country="United States",
            media_name="Test News",
            homepage_url="https://example.com",
            found_coverage=False,
            error="KeyError: 'structured_response' not in agent output",
        )

        assert result.found_coverage is False
        assert result.article is None
        assert "KeyError" in result.error

    def test_no_coverage_found_result(self):
        """Result with no coverage found should pass."""
        result = SourceProcessingResult(
            country="United States",
            media_name="Test News",
            homepage_url="https://example.com",
            found_coverage=False,
        )

        assert result.found_coverage is False
        assert result.article is None
        assert result.error is None


class TestSelectedSource:
    """Test SelectedSource schema."""

    def test_valid_selected_source(self):
        """Valid selected source should pass."""
        source = SelectedSource(
            country="United States",
            media_name="CNN",
            url="https://edition.cnn.com",
            priority="high",
        )

        assert source.priority == "high"

    def test_invalid_priority_should_fail(self):
        """Invalid priority literal should fail."""
        with pytest.raises(ValidationError, match="priority"):
            SelectedSource(
                country="United States",
                media_name="CNN",
                url="https://edition.cnn.com",
                priority="critical",  # Invalid - not in Literal
            )


class TestPlanningOutput:
    """Test PlanningOutput schema."""

    def test_valid_planning_output(self):
        """Valid planning output should pass."""
        output = PlanningOutput(
            topic="Venezuela crisis",
            selected_sources=[
                SelectedSource(
                    country="United States",
                    media_name="CNN",
                    url="https://edition.cnn.com",
                    priority="high",
                ),
                SelectedSource(
                    country="United Kingdom",
                    media_name="BBC",
                    url="https://www.bbc.com",
                    priority="high",
                ),
            ],
            rationale="Selected major international news sources with comprehensive coverage.",
        )

        assert len(output.selected_sources) == 2
        assert output.topic == "Venezuela crisis"

    def test_empty_sources_list_should_fail(self):
        """Empty selected_sources list should fail (min_length=1)."""
        with pytest.raises(ValidationError, match="min_length"):
            PlanningOutput(
                topic="Venezuela crisis",
                selected_sources=[],
                rationale="No sources selected.",
            )

    def test_too_many_sources_should_fail(self):
        """More than 15 sources should fail (max_length=15)."""
        sources = [
            SelectedSource(
                country=f"Country {i}",
                media_name=f"Media {i}",
                url=f"https://example{i}.com",
                priority="medium",
            )
            for i in range(20)
        ]

        with pytest.raises(ValidationError, match="max_length"):
            PlanningOutput(
                topic="Test topic",
                selected_sources=sources,
                rationale="Too many sources selected.",
            )


class TestMediaComparison:
    """Test MediaComparison schema."""

    def test_valid_media_comparison(self):
        """Valid media comparison row should pass."""
        comparison = MediaComparison(
            country="United States",
            media_name="CNN",
            article_title="Venezuela Crisis Deepens",
            article_url="https://example.com/article",
            core_viewpoint="Analysis of the diplomatic implications",
        )

        assert comparison.media_name == "CNN"


class TestAggregationOutput:
    """Test AggregationOutput schema."""

    def test_valid_aggregation_output(self):
        """Valid aggregation output should pass."""
        output = AggregationOutput(
            topic="Venezuela crisis",
            total_sources_checked=10,
            sources_with_coverage=5,
            comparison_table=[
                MediaComparison(
                    country="United States",
                    media_name="CNN",
                    article_title="Venezuela Crisis Deepens",
                    article_url="https://example.com/article",
                    core_viewpoint="Analysis of the diplomatic implications",
                )
            ],
            summary="Coverage varies across sources with some emphasizing diplomatic solutions.",
            processing_timestamp="2026-01-12T23:52:34.873511",
        )

        assert output.sources_with_coverage == 5
        assert len(output.comparison_table) == 1

    def test_empty_comparison_table_allowed(self):
        """Empty comparison table should be allowed (no sources found)."""
        output = AggregationOutput(
            topic="Venezuela crisis",
            total_sources_checked=10,
            sources_with_coverage=0,
            comparison_table=[],
            summary="No articles were found covering this topic.",
            processing_timestamp="2026-01-12T23:52:34.873511",
        )

        assert len(output.comparison_table) == 0
        assert output.sources_with_coverage == 0
