"""Core extraction logic and error handling.

This module provides functions for validating agent responses, creating
extraction results, and handling errors uniformly across the pipeline.
"""

import logging
import time
import traceback
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from logging_utils import (
    append_to_jsonl,
    log_agent_call,
    log_extraction_attempt,
    log_response_structure,
)
from schemas import ArticleExtraction, SelectedSource, SourceProcessingResult


def validate_agent_response(
    response: dict[str, Any],
    source: SelectedSource,
    logger: logging.Logger | None = None,
) -> ArticleExtraction:
    """Validate agent response contains structured_response.

    Args:
        response: Agent response dictionary
        source: Source being processed
        logger: Optional logger for debugging

    Returns:
        ArticleExtraction from response

    Raises:
        KeyError: If structured_response key is missing

    Example:
        try:
            article = validate_agent_response(response, source, logger)
        except KeyError as e:
            # Handle missing structured_response
            pass
    """
    # Log response structure for debugging
    if logger:
        log_response_structure(logger, source.media_name, response)

    # Check if structured_response exists
    if "structured_response" not in response:
        error_msg = (
            f"No 'structured_response' in agent output. "
            f"Available keys: {list(response.keys())}"
        )
        if logger:
            logger.error(
                f"Missing structured_response for {source.media_name}",
                extra={
                    "response_keys": list(response.keys()),
                    "response": str(response)[:500],
                },
            )
        raise KeyError(error_msg)

    return response["structured_response"]


def create_error_result(
    source: SelectedSource,
    error: Exception,
    error_type: str = "generic",
) -> SourceProcessingResult:
    """Create SourceProcessingResult for failed extraction.

    Args:
        source: Source that failed
        error: Exception that occurred
        error_type: Type of error (for better error messages)

    Returns:
        SourceProcessingResult with error details

    Example:
        result = create_error_result(source, exception, "validation")
    """
    error_msg = f"{type(error).__name__}: {str(error)}"

    return SourceProcessingResult(
        country=source.country,
        media_name=source.media_name,
        homepage_url=source.url,
        found_coverage=False,
        error=error_msg,
    )


def handle_extraction_error(
    error: Exception,
    source: SelectedSource,
    topic: str,
    start_time: float,
    logger: logging.Logger | None = None,
    run_dir: Path | None = None,
    response: dict[str, Any] | None = None,
) -> SourceProcessingResult:
    """Handle extraction error with logging and result creation.

    This function provides unified error handling for all extraction errors,
    including KeyError, ValidationError, and generic exceptions. It logs
    appropriately based on error type and creates an error result.

    Args:
        error: Exception that occurred
        source: Source being processed
        topic: Topic being searched
        start_time: Start time for duration calculation
        logger: Optional logger
        run_dir: Optional run directory for output
        response: Optional agent response (for KeyError/ValidationError)

    Returns:
        SourceProcessingResult with error details

    Example:
        try:
            # extraction logic
            pass
        except (KeyError, ValidationError, Exception) as e:
            return handle_extraction_error(e, source, topic, start_time, logger)
    """
    duration_ms = (time.time() - start_time) * 1000
    error_msg = f"{type(error).__name__}: {str(error)}"

    # Type-specific logging
    if isinstance(error, ValidationError):
        if logger:
            logger.error(
                f"Validation failed for {source.media_name}",
                extra={
                    "validation_errors": error.errors(),
                    "raw_data": (
                        response.get("structured_response") if response else None
                    ),
                },
            )
    elif isinstance(error, KeyError):
        # Already logged in validate_agent_response
        pass
    else:
        # Check if this is a transient tool/network error
        is_tool_error = "ToolException" in type(error).__name__

        if logger:
            if is_tool_error:
                # Transient tool errors - log at WARNING without traceback
                logger.warning(
                    f"Tool error for {source.media_name}: {str(error)[:200]}",
                    extra={"error_type": type(error).__name__},
                )
            else:
                # Unexpected errors - log at ERROR with traceback
                logger.exception(
                    f"Unexpected error for {source.media_name}",
                    extra={
                        "error_type": type(error).__name__,
                        "traceback": traceback.format_exc(),
                    },
                )

    # Log agent call
    if logger:
        log_agent_call(
            logger,
            "extraction",
            source.media_name,
            {"url": source.url, "topic": topic},
            response,
            error,
            duration_ms,
        )
        log_extraction_attempt(
            logger, source.media_name, source.url, False, None, error_msg
        )

    return create_error_result(source, error)


def create_success_result(
    source: SelectedSource,
    article: ArticleExtraction,
    response: dict[str, Any],
    topic: str,
    start_time: float,
    logger: logging.Logger | None = None,
    run_dir: Path | None = None,
) -> SourceProcessingResult:
    """Create successful SourceProcessingResult with logging.

    Args:
        source: Source that succeeded
        article: Extracted article
        response: Agent response
        topic: Topic searched
        start_time: Start time for duration calculation
        logger: Optional logger
        run_dir: Optional run directory for output

    Returns:
        SourceProcessingResult with article

    Example:
        result = create_success_result(
            source, article, response, topic, start_time, logger, run_dir
        )
    """
    duration_ms = (time.time() - start_time) * 1000

    # Log successful extraction
    if logger:
        log_agent_call(
            logger,
            "extraction",
            source.media_name,
            {"url": source.url, "topic": topic},
            response,
            None,
            duration_ms,
        )
        log_extraction_attempt(
            logger,
            source.media_name,
            source.url,
            True,
            article.model_dump(mode="json") if article else None,
            None,
        )

    # Save raw response for debugging
    if run_dir:
        append_to_jsonl(
            run_dir,
            "extraction_responses",
            {"source": source.media_name, "response": response},
        )

    result = SourceProcessingResult(
        country=source.country,
        media_name=source.media_name,
        homepage_url=source.url,
        found_coverage=True,
        article=article,
    )

    return result
