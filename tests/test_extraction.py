"""Tests for the extraction phase of the pipeline.

Tests the extract_from_source function with mocked MCP sessions and agents.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from schemas import SelectedSource, SourceProcessingResult, ArticleExtraction


@pytest.fixture
def mock_session():
    """Mock MCP ClientSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_source():
    """Sample news source for testing."""
    return SelectedSource(
        country="United States",
        media_name="Test News Network",
        url="https://example-news.com",
        priority="high",
    )


class TestExtractFromSource:
    """Test the extract_from_source function with various scenarios."""

    @pytest.mark.asyncio
    async def test_successful_extraction_with_valid_article(
        self, mock_session, sample_source
    ):
        """Test successful extraction with valid article data."""
        # Import here to avoid circular dependencies
        from main import extract_from_source

        # Mock the agent response with valid ArticleExtraction
        mock_article = ArticleExtraction(
            headline="Venezuela President Faces International Pressure Crisis",
            article_url="https://example-news.com/venezuela-article-123",
            core_viewpoint="The article discusses international diplomatic efforts to resolve the Venezuela crisis through multilateral negotiations and sanctions.",
            publication_date="2026-01-12",
        )

        with patch("main.create_extraction_agent") as mock_create_agent:
            mock_agent = AsyncMock()
            mock_agent.ainvoke.return_value = {"structured_response": mock_article}
            mock_create_agent.return_value = mock_agent

            result = await extract_from_source(
                sample_source, "Venezuela crisis", mock_session
            )

            # Assertions
            assert isinstance(result, SourceProcessingResult)
            assert result.found_coverage is True
            assert result.article is not None
            assert (
                result.article.headline
                == "Venezuela President Faces International Pressure Crisis"
            )
            assert (
                str(result.article.article_url)
                == "https://example-news.com/venezuela-article-123"
            )
            assert len(result.article.core_viewpoint) > 20
            assert result.error is None

    @pytest.mark.asyncio
    async def test_missing_structured_response_key(self, mock_session, sample_source):
        """Test handling when agent response doesn't have 'structured_response' key.

        This reproduces the suspected failure mode where response["structured_response"]
        raises KeyError.
        """
        from main import extract_from_source

        with patch("main.create_extraction_agent") as mock_create_agent:
            mock_agent = AsyncMock()
            # Response missing the structured_response key
            mock_agent.ainvoke.return_value = {
                "messages": ["some", "data"],
                "output": "raw text output from agent",
            }
            mock_create_agent.return_value = mock_agent

            result = await extract_from_source(
                sample_source, "Venezuela crisis", mock_session
            )

            # Should return failed result, not raise exception
            assert isinstance(result, SourceProcessingResult)
            assert result.found_coverage is False
            assert result.article is None
            assert result.error is not None
            # Error should mention KeyError or structured_response
            assert "KeyError" in result.error or "structured_response" in result.error

    @pytest.mark.asyncio
    async def test_empty_article_fields(self, mock_session, sample_source):
        """Test handling when article has empty fields (should fail validation)."""
        from main import extract_from_source

        # Mock agent response with empty fields - this will raise ValidationError
        # during ArticleExtraction creation, not during extract_from_source
        with patch("main.create_extraction_agent") as mock_create_agent:
            mock_agent = AsyncMock()
            # Return raw dict that will fail ArticleExtraction validation
            mock_agent.ainvoke.return_value = {
                "structured_response": {
                    "headline": "",
                    "article_url": "https://example.com/article",
                    "core_viewpoint": "",
                }
            }
            mock_create_agent.return_value = mock_agent

            result = await extract_from_source(
                sample_source, "Venezuela crisis", mock_session
            )

            # Should fail with validation error
            assert result.found_coverage is False
            assert result.error is not None
            # Error should mention validation or empty fields
            assert any(
                keyword in result.error.lower()
                for keyword in ["validation", "string", "characters"]
            )

    @pytest.mark.asyncio
    async def test_invalid_article_url_format(self, mock_session, sample_source):
        """Test handling when article URL is invalid format."""
        from main import extract_from_source

        with patch("main.create_extraction_agent") as mock_create_agent:
            mock_agent = AsyncMock()
            # Return raw dict with invalid URL
            mock_agent.ainvoke.return_value = {
                "structured_response": {
                    "headline": "Valid headline here that is long enough",
                    "article_url": "not-a-valid-url",
                    "core_viewpoint": "This is a valid core viewpoint with enough words to pass minimum word count requirements.",
                }
            }
            mock_create_agent.return_value = mock_agent

            result = await extract_from_source(
                sample_source, "Venezuela crisis", mock_session
            )

            # Should fail with URL validation error
            assert result.found_coverage is False
            assert result.error is not None
            assert any(
                keyword in result.error.lower() for keyword in ["validation", "url"]
            )

    @pytest.mark.asyncio
    async def test_agent_raises_exception(self, mock_session, sample_source):
        """Test handling when agent.ainvoke raises an exception."""
        from main import extract_from_source

        with patch("main.create_extraction_agent") as mock_create_agent:
            mock_agent = AsyncMock()
            # Agent raises exception
            mock_agent.ainvoke.side_effect = RuntimeError("MCP connection failed")
            mock_create_agent.return_value = mock_agent

            result = await extract_from_source(
                sample_source, "Venezuela crisis", mock_session
            )

            # Should catch exception and return failed result
            assert result.found_coverage is False
            assert result.article is None
            assert result.error is not None
            assert (
                "RuntimeError" in result.error
                or "MCP connection failed" in result.error
            )

    @pytest.mark.asyncio
    async def test_placeholder_text_in_fields(self, mock_session, sample_source):
        """Test handling when article contains placeholder text."""
        from main import extract_from_source

        with patch("main.create_extraction_agent") as mock_create_agent:
            mock_agent = AsyncMock()
            # Return raw dict with placeholder text
            mock_agent.ainvoke.return_value = {
                "structured_response": {
                    "headline": "N/A",
                    "article_url": "https://example.com/article",
                    "core_viewpoint": "None",
                }
            }
            mock_create_agent.return_value = mock_agent

            result = await extract_from_source(
                sample_source, "Venezuela crisis", mock_session
            )

            # Placeholders should be rejected
            assert result.found_coverage is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_very_short_viewpoint(self, mock_session, sample_source):
        """Test handling when viewpoint is too short (< 10 words)."""
        from main import extract_from_source

        with patch("main.create_extraction_agent") as mock_create_agent:
            mock_agent = AsyncMock()
            # Return raw dict with short viewpoint
            mock_agent.ainvoke.return_value = {
                "structured_response": {
                    "headline": "Valid headline here that is long enough",
                    "article_url": "https://example.com/article",
                    "core_viewpoint": "Too short.",
                }
            }
            mock_create_agent.return_value = mock_agent

            result = await extract_from_source(
                sample_source, "Venezuela crisis", mock_session
            )

            # Short viewpoints should be rejected
            assert result.found_coverage is False
            assert result.error is not None


class TestExtractFromSourcesIntegration:
    """Integration tests for batch extraction."""

    @pytest.mark.asyncio
    async def test_batch_processing_with_mixed_results(self):
        """Test batch processing with some successes and some failures."""
        from main import extract_from_sources

        sources = [
            SelectedSource(
                country="United States",
                media_name="Success News",
                url="https://success.com",
                priority="high",
            ),
            SelectedSource(
                country="United Kingdom",
                media_name="Fail News",
                url="https://fail.com",
                priority="medium",
            ),
        ]

        # Mock successful article
        mock_success_article = ArticleExtraction(
            headline="Venezuela Crisis Update with Full Coverage",
            article_url="https://success.com/article",
            core_viewpoint="Comprehensive analysis of the Venezuela situation with multiple expert perspectives included here.",
        )

        def mock_extract_side_effect(source, topic, session, logger=None, run_dir=None):
            """Mock that returns success for first source, failure for second."""
            if "success" in source.url:
                return SourceProcessingResult(
                    country=source.country,
                    media_name=source.media_name,
                    homepage_url=source.url,
                    found_coverage=True,
                    article=mock_success_article,
                )
            else:
                return SourceProcessingResult(
                    country=source.country,
                    media_name=source.media_name,
                    homepage_url=source.url,
                    found_coverage=False,
                    error="KeyError: 'structured_response'",
                )

        with patch("main.extract_from_source", side_effect=mock_extract_side_effect):
            results = await extract_from_sources(sources, "Venezuela crisis")

            assert len(results) == 2
            assert results[0].found_coverage is True
            assert results[0].article is not None
            assert results[1].found_coverage is False
            assert results[1].error is not None
