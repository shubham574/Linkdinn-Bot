"""Deterministic placeholders so the graph runs end-to-end before Phase 2-4.
Replaced by Gemini (research/write/rewrite/fact-check) and Laya (topic select/rating)."""
from typing import Any

from app.agents.base import FactCheckResult, PostRating, ResearchPackage, TopicSelection


class StubResearcher:
    def discover(self, target_date, previous_topics):
        return [{"title": "Stub topic A", "summary": "placeholder"},
                {"title": "Stub topic B", "summary": "placeholder"}]

    def deep_research(self, topic):
        return ResearchPackage(
            topic=topic["title"], summary="Placeholder research summary.",
            facts=["Placeholder fact."],
            sources=[{"title": "stub", "url": "https://example.com", "publisher": "stub"}],
        )


class StubTopicSelector:
    def select(self, candidates, previous_topics):
        fresh = [c for c in candidates if c["title"] not in previous_topics]
        return TopicSelection(selected=fresh[0] if fresh else None,
                              rejected=[c for c in candidates if c not in fresh[:1]])


class StubMemory:
    def previous_topics(self): return []
    def personal_context(self, topic): return []
    def previous_posts(self, topic): return []


class StubWriter:
    def write(self, state: dict[str, Any]) -> str:
        return f"[stub draft about {state['selected_topic']['title']}]"


class StubRewriter:
    def rewrite(self, state: dict[str, Any]) -> str:
        return (state.get("revised_post") or state["draft_post"]) + " (revised)"


class StubRater:
    def rate(self, post, state):
        return PostRating(human_naturalness=90, generic_ai_language=10, personal_voice=70,
                          specificity=80, originality=70, usefulness=80, readability=90,
                          factual_confidence=95, fabricated_personal_claim_prob=0.0)


class StubFactChecker:
    def check(self, post, sources, state):
        return FactCheckResult(passed=True)
