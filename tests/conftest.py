import pytest

from app.agents import stubs
from app.agents.base import FactCheckResult, PostRating, ResearchPackage
from app.config import Settings
from app.graph.nodes import Deps
from app.graph.workflow import build_workflow


def rating(good: bool = True, **over) -> PostRating:
    base = dict(human_naturalness=92, generic_ai_language=10, personal_voice=70, specificity=80,
                originality=70, usefulness=80, readability=90, factual_confidence=95,
                fabricated_personal_claim_prob=0.0)
    if not good:
        base.update(human_naturalness=60, generic_ai_language=70,
                    problems=["generic opening"], rewrite_instructions=["make opening natural"])
    base.update(over)
    return PostRating(**base)


class ScriptedRater:
    def __init__(self, seq): self.seq, self.calls = list(seq), 0
    def rate(self, post, state):
        self.calls += 1
        item = self.seq[min(self.calls - 1, len(self.seq) - 1)]
        if isinstance(item, Exception): raise item
        return item


class ScriptedFactChecker:
    def __init__(self, seq): self.seq, self.calls = list(seq), 0
    def check(self, post, sources, state):
        self.calls += 1
        ok = self.seq[min(self.calls - 1, len(self.seq) - 1)]
        return FactCheckResult(passed=ok, unsupported_claims=[] if ok else ["claim X"])


class RecordingPublisher:
    def __init__(self, fail=False): self.calls, self.fail = [], fail
    def publish(self, text, run_id):
        self.calls.append((text, run_id))
        if self.fail: raise RuntimeError("linkedin 500")
        return "urn:li:share:123"


class MemoryRepo:
    def __init__(self): self.saved = []
    def save_result(self, state): self.saved.append(state)


class EmptyResearcher(stubs.StubResearcher):
    def discover(self, *a): return []


class NoSourcesResearcher(stubs.StubResearcher):
    def deep_research(self, topic): return ResearchPackage(topic=topic["title"])


@pytest.fixture
def make_graph():
    def _make(rater=None, fact=None, publisher=None, researcher=None, repo=None, **settings):
        s = Settings(_env_file=None, **settings)
        repo = repo or MemoryRepo()
        deps = Deps(
            settings=s, researcher=researcher or stubs.StubResearcher(),
            selector=stubs.StubTopicSelector(), memory=stubs.StubMemory(),
            writer=stubs.StubWriter(), rewriter=stubs.StubRewriter(),
            rater=rater or ScriptedRater([rating()]), fact_checker=fact or ScriptedFactChecker([True]),
            repository=repo, publisher=publisher,
        )
        return build_workflow(deps), repo
    return _make


def initial(run_id="r1"):
    return {"run_id": run_id, "target_date": "2026-09-23", "errors": [], "status": "running"}
