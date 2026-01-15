"""Logging utilities for debugging the news aggregation pipeline.

Provides structured logging to capture all phase inputs, outputs, and errors.
"""

import json
import logging
from pathlib import Path
from typing import Any
from datetime import datetime


def setup_phase_logging(run_id: str, phase: str) -> tuple[logging.Logger, Path]:
    """Set up logging for a specific phase of the pipeline.

    Args:
        run_id: Unique identifier for this run (e.g., timestamp)
        phase: Phase name (e.g., "planning", "extraction", "aggregation")

    Returns:
        Tuple of (logger instance, run directory path)
    """
    # Create run directory
    run_dir = Path("runs") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger(f"nexus.{phase}")
    logger.setLevel(logging.DEBUG)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Custom formatter for JSON output
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "level": record.levelname,
                "phase": phase,
                "message": record.getMessage(),
            }
            # Include extra fields from record (they become attributes)
            for key, value in record.__dict__.items():
                if key not in [
                    "name",
                    "msg",
                    "args",
                    "created",
                    "filename",
                    "funcName",
                    "levelname",
                    "levelno",
                    "lineno",
                    "module",
                    "msecs",
                    "message",
                    "pathname",
                    "process",
                    "processName",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "getMessage",
                    "asctime",
                ]:
                    log_data[key] = value
            return json.dumps(log_data, ensure_ascii=False)

    # Console handler (INFO and above) - Structured JSON
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)

    # File handler for JSON lines (all levels)
    log_file = run_dir / f"{phase}_log.jsonl"
    file_handler = logging.FileHandler(log_file, mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    logger.info(f"Logging initialized for phase: {phase}", extra={"run_id": run_id})

    return logger, run_dir


def log_agent_call(
    logger: logging.Logger,
    phase: str,
    source_name: str | None,
    input_data: dict[str, Any],
    response: dict[str, Any] | None = None,
    error: Exception | None = None,
    duration_ms: float | None = None,
) -> None:
    """Log an agent invocation with full details.

    Args:
        logger: Logger instance
        phase: Phase name
        source_name: Name of the source being processed (for extraction phase)
        input_data: Input data sent to agent
        response: Agent response dict (if successful)
        error: Exception if agent call failed
        duration_ms: Duration in milliseconds
    """
    log_entry = {
        "event": "agent_call",
        "phase": phase,
        "source_name": source_name,
        "duration_ms": duration_ms,
    }

    # Log input summary (not full content to avoid huge logs)
    if input_data:
        log_entry["input_keys"] = list(input_data.keys())
        if "messages" in input_data and input_data["messages"]:
            log_entry["input_message_count"] = len(input_data["messages"])

    # Log response structure
    if response:
        log_entry["response_keys"] = list(response.keys())
        log_entry["has_structured_response"] = "structured_response" in response

        if "structured_response" in response:
            structured_resp = response["structured_response"]
            log_entry["structured_response_type"] = str(type(structured_resp).__name__)

            # Try to serialize to JSON for inspection
            try:
                if hasattr(structured_resp, "model_dump"):
                    log_entry["structured_response_data"] = structured_resp.model_dump(mode='json')
                else:
                    log_entry["structured_response_data"] = str(structured_resp)
            except Exception as e:
                log_entry["structured_response_serialization_error"] = str(e)

    # Log error details
    if error:
        log_entry["error_type"] = type(error).__name__
        log_entry["error_message"] = str(error)
        log_entry["success"] = False
    else:
        log_entry["success"] = True

    logger.info(
        f"Agent call {'succeeded' if not error else 'failed'} for {source_name or phase}",
        extra=log_entry,
    )


def _make_json_serializable(obj: Any) -> Any:
    """Recursively convert objects to JSON-serializable forms.

    Filters out non-serializable objects like LangChain messages.

    Args:
        obj: Object to convert

    Returns:
        JSON-serializable version of the object
    """
    from langchain_core.messages import BaseMessage

    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            # Skip the 'messages' key entirely (contains LangChain messages)
            if key == "messages":
                continue
            result[key] = _make_json_serializable(value)
        return result

    elif isinstance(obj, list):
        # Filter out LangChain message objects
        return [
            _make_json_serializable(item)
            for item in obj
            if not isinstance(item, BaseMessage)
        ]

    elif hasattr(obj, "model_dump"):
        # Pydantic models
        return obj.model_dump(mode='json')

    elif isinstance(obj, (str, int, float, bool, type(None))):
        # Primitives
        return obj

    else:
        # For other types, convert to string representation
        return str(obj)


def save_phase_output(
    run_dir: Path,
    phase: str,
    filename: str,
    data: Any,
) -> Path:
    """Save phase output to a JSON file.

    Args:
        run_dir: Run directory path
        phase: Phase name
        filename: Output filename (without extension)
        data: Data to save (will be JSON serialized)

    Returns:
        Path to saved file
    """
    output_file = run_dir / f"{phase}_{filename}.json"

    # Convert Pydantic models to dicts
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode='json')
    elif isinstance(data, list) and data and hasattr(data[0], "model_dump"):
        data = [item.model_dump(mode='json') for item in data]
    # Handle dicts with mixed types (e.g., agent responses)
    elif isinstance(data, dict):
        data = _make_json_serializable(data)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return output_file


def log_extraction_attempt(
    logger: logging.Logger,
    source_name: str,
    url: str,
    found_coverage: bool,
    article_data: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """Log an extraction attempt with results.

    Args:
        logger: Logger instance
        source_name: Name of the source
        url: URL visited
        found_coverage: Whether coverage was found
        article_data: Extracted article data if successful
        error: Error message if failed
    """
    log_entry = {
        "event": "extraction_attempt",
        "source_name": source_name,
        "url": url,
        "found_coverage": found_coverage,
    }

    if article_data:
        log_entry["article_headline"] = article_data.get("headline", "")
        log_entry["article_url"] = article_data.get("article_url", "")
        log_entry["viewpoint_length"] = len(article_data.get("core_viewpoint", ""))

    if error:
        log_entry["error"] = error

    level = logging.INFO if found_coverage else logging.WARNING
    message = (
        f"✓ {source_name}: Found coverage"
        if found_coverage
        else f"✗ {source_name}: No coverage"
    )
    if error:
        message += f" ({error})"

    logger.log(level, message, extra=log_entry)


def log_response_structure(
    logger: logging.Logger,
    source_name: str,
    response: dict[str, Any],
) -> None:
    """Log the structure of an agent response for debugging.

    Args:
        logger: Logger instance
        source_name: Name of the source
        response: Agent response dict
    """
    log_entry = {
        "event": "response_structure_inspection",
        "source_name": source_name,
        "response_keys": list(response.keys()),
        "response_type": str(type(response)),
    }

    # Inspect each key
    for key, value in response.items():
        log_entry[f"key_{key}_type"] = str(type(value))
        log_entry[f"key_{key}_is_none"] = value is None

        # For structured_response, get more details
        if key == "structured_response" and value is not None:
            log_entry[f"key_{key}_class"] = type(value).__name__
            if hasattr(value, "model_fields"):
                log_entry[f"key_{key}_fields"] = list(value.model_fields.keys())

    logger.debug(f"Response structure for {source_name}", extra=log_entry)


def log_phase_start(
    logger: logging.Logger,
    phase: str,
    extra_data: dict[str, Any] | None = None,
) -> None:
    """Log the start of a pipeline phase.

    Args:
        logger: Logger instance
        phase: Phase name
        extra_data: Additional context (e.g., topic, source count)
    """
    log_entry = {"event": "phase_start", "phase": phase}
    if extra_data:
        log_entry.update(extra_data)
    logger.info(f"{phase.capitalize()} phase started", extra=log_entry)


def log_phase_complete(
    logger: logging.Logger,
    phase: str,
    summary_data: dict[str, Any],
) -> None:
    """Log the completion of a pipeline phase with summary.

    Args:
        logger: Logger instance
        phase: Phase name
        summary_data: Summary metrics (e.g., success count, duration)
    """
    log_entry = {
        "event": "phase_complete",
        "phase": phase,
        "summary": summary_data,
    }
    logger.info(f"{phase.capitalize()} phase complete", extra=log_entry)


def log_batch_start(
    logger: logging.Logger,
    batch_num: int,
    total_batches: int,
    sources: list[str],
) -> None:
    """Log the start of a batch in extraction phase.

    Args:
        logger: Logger instance
        batch_num: Current batch number (1-indexed)
        total_batches: Total number of batches
        sources: List of source names in this batch
    """
    log_entry = {
        "event": "batch_start",
        "batch_num": batch_num,
        "total_batches": total_batches,
        "sources": sources,
        "source_count": len(sources),
    }
    logger.info(
        f"Batch {batch_num}/{total_batches}: Processing {', '.join(sources)}",
        extra=log_entry,
    )


def log_batch_complete(
    logger: logging.Logger,
    batch_num: int,
    results: list[Any],
) -> None:
    """Log the completion of a batch with results summary.

    Args:
        logger: Logger instance
        batch_num: Current batch number
        results: Batch processing results
    """
    successful = sum(
        1 for r in results if hasattr(r, "found_coverage") and r.found_coverage
    )
    failed = len(results) - successful

    log_entry = {
        "event": "batch_complete",
        "batch_num": batch_num,
        "total_in_batch": len(results),
        "successful": successful,
        "failed": failed,
    }
    logger.info(
        f"Batch {batch_num} complete: {successful}/{len(results)} successful",
        extra=log_entry,
    )
