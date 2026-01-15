"""Pipeline configuration models."""

import os

from pydantic import BaseModel, Field


class PipelineConfig(BaseModel):
    """Configuration for the news aggregation pipeline."""

    topic: str = Field(description="News topic to search for")
    num_sources: int = Field(default=10, description="Number of sources to select")
    model: str = Field(default="deepseek-chat", description="LLM model to use")


def load_config() -> PipelineConfig:
    """Load pipeline configuration from environment variables."""
    return PipelineConfig(
        topic=os.getenv("NEWS_TOPIC", ""),
        num_sources=int(os.getenv("NEWS_NUM_SOURCES", "10")),
        model=os.getenv("NEWS_MODEL", "deepseek-chat"),
    )
