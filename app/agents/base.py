"""Agent interfaces + structured output models.

The graph depends only on these Protocols, so Gemini/Laya/Tavily implementations
(Phases 2-4) can be swapped in without touching the workflow.
"""
from typing import Any, Protocol

from pydantic import BaseModel, Field


class ResearchPackage(BaseModel):
    topic: str
    why_relevant: str = ""
    summary: str = ""
    facts: list[str] = Field(default_factory=list)
    developer_implications: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    possible_angles: list[str] = Field(default_factory=list)


class TopicSelection(BaseModel):
    selected: dict[str, Any] | None
    rejected: list[dict[str, Any]] = Field(default_factory=list)


class PostRating(BaseModel):
    """Structured quality rating. Scores 0-100 (higher better) unless noted."""

    human_naturalness: int = Field(ge=0, le=100)
    generic_ai_language: int = Field(ge=0, le=100)  # LOWER is better
    personal_voice: int = Field(ge=0, le=100)
    specificity: int = Field(ge=0, le=100)
    originality: int = Field(ge=0, le=100)
    usefulness: int = Field(ge=0, le=100)
    readability: int = Field(ge=0, le=100)
    factual_confidence: int = Field(ge=0, le=100)
    fabricated_personal_claim_prob: float = Field(ge=0.0, le=1.0)  # LOWER is better
    problems: list[str] = Field(default_factory=list)
    rewrite_instructions: list[str] = Field(default_factory=list)


class FactCheckResult(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)
    verified_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)


class Researcher(Protocol):
    def discover(self, target_date: str, previous_topics: list[str]) -> list[dict[str, Any]]: ...
    def deep_research(self, topic: dict[str, Any]) -> ResearchPackage: ...


class TopicSelector(Protocol):
    def select(self, candidates: list[dict[str, Any]], previous_topics: list[str]) -> TopicSelection: ...


class MemoryStore(Protocol):
    def previous_topics(self) -> list[str]: ...
    def personal_context(self, topic: dict[str, Any]) -> list[dict[str, Any]]: ...
    def previous_posts(self, topic: dict[str, Any]) -> list[dict[str, Any]]: ...


class Writer(Protocol):
    def write(self, state: dict[str, Any]) -> str: ...


class Rewriter(Protocol):
    def rewrite(self, state: dict[str, Any]) -> str: ...


class PostRater(Protocol):
    def rate(self, post: str, state: dict[str, Any]) -> PostRating: ...


class FactChecker(Protocol):
    def check(self, post: str, sources: list[dict[str, Any]], state: dict[str, Any]) -> FactCheckResult: ...


class Publisher(Protocol):
    def publish(self, text: str, run_id: str) -> str:
        """Return the LinkedIn post id."""
        ...


class Repository(Protocol):
    def save_result(self, state: dict[str, Any]) -> None: ...
