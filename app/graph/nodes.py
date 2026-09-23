import logging
from dataclasses import dataclass
from typing import Any

from app.agents.base import (
    FactChecker, MemoryStore, PostRater, Publisher, Repository, Researcher, Rewriter,
    TopicSelector, Writer,
)
from app.config import Settings
from app.graph.state import (
    AWAITING_APPROVAL, DRY_RUN_COMPLETE, MANUAL_REVIEW, PUBLISHED, ContentState, current_post,
)
from app.services.content_service import evaluate_approval

log = logging.getLogger("linkedin_agent")


@dataclass
class Deps:
    settings: Settings
    researcher: Researcher
    selector: TopicSelector
    memory: MemoryStore
    writer: Writer
    rewriter: Rewriter
    rater: PostRater
    fact_checker: FactChecker
    repository: Repository
    publisher: Publisher | None = None


def _fail(state: ContentState, node: str, msg: str) -> dict[str, Any]:
    log.error("run=%s node=%s failed: %s", state.get("run_id"), node, msg)
    return {"errors": [f"{node}: {msg}"], "status": MANUAL_REVIEW}


def build_nodes(deps: Deps) -> dict[str, Any]:
    s = deps.settings

    def research(state: ContentState) -> dict[str, Any]:
        log.info("run=%s agent=research started", state["run_id"])
        try:
            candidates = deps.researcher.discover(state["target_date"], deps.memory.previous_topics())
        except Exception as e:  # search API failure etc.
            return _fail(state, "research", f"{type(e).__name__}: {e}")
        if not candidates:
            return _fail(state, "research", "no candidate topics found")
        return {"candidate_topics": candidates}

    def select_topic(state: ContentState) -> dict[str, Any]:
        try:
            sel = deps.selector.select(state["candidate_topics"], deps.memory.previous_topics())
        except Exception as e:
            return _fail(state, "select_topic", f"{type(e).__name__}: {e}")
        if sel.selected is None:
            return _fail(state, "select_topic", "no suitable topic")
        log.info("run=%s topic selected: %s", state["run_id"], sel.selected.get("title"))
        return {"selected_topic": sel.selected, "rejected_topics": sel.rejected}

    def build_context(state: ContentState) -> dict[str, Any]:
        topic = state["selected_topic"]
        try:
            pkg = deps.researcher.deep_research(topic)
        except Exception as e:
            return _fail(state, "build_context", f"{type(e).__name__}: {e}")
        if not pkg.sources or not (pkg.facts or pkg.summary):
            return _fail(state, "build_context", "required research missing (no sources/facts)")
        return {
            "research_results": [pkg.model_dump()],
            "research_summary": pkg.summary,
            "research_sources": pkg.sources,
            "personal_context": deps.memory.personal_context(topic),
            "relevant_previous_posts": deps.memory.previous_posts(topic),
            "revision_count": 0,
            "max_revisions": s.max_revisions,
        }

    def write_post(state: ContentState) -> dict[str, Any]:
        try:
            text = deps.writer.write(state)
        except Exception as e:
            return _fail(state, "write_post", f"{type(e).__name__}: {e}")
        if not text.strip():
            return _fail(state, "write_post", "writer returned empty text")
        return {"draft_post": text, "approved": False, "fact_checked": False}

    def review_post(state: ContentState) -> dict[str, Any]:
        try:
            rating = deps.rater.rate(current_post(state), state)
        except Exception as e:  # includes invalid structured output
            return _fail(state, "review_post", f"invalid rater output: {type(e).__name__}: {e}")
        decision = evaluate_approval(rating, s)
        log.info("run=%s review approved=%s revision=%s", state["run_id"], decision.approved,
                 state.get("revision_count", 0))
        return {
            "approved": decision.approved,
            "review_result": {**rating.model_dump(), "approved": decision.approved,
                              "failed_criteria": decision.failed_criteria},
        }

    def rewrite_post(state: ContentState) -> dict[str, Any]:
        try:
            text = deps.rewriter.rewrite(state)
        except Exception as e:
            return _fail(state, "rewrite_post", f"{type(e).__name__}: {e}")
        if not text.strip():
            return _fail(state, "rewrite_post", "rewriter returned empty text")
        return {
            "revised_post": text,
            "revision_count": state.get("revision_count", 0) + 1,
            "approved": False,
            "fact_checked": False,
        }

    def fact_check(state: ContentState) -> dict[str, Any]:
        post = current_post(state)
        try:
            result = deps.fact_checker.check(post, state.get("research_sources", []), state)
        except Exception as e:
            return _fail(state, "fact_check", f"{type(e).__name__}: {e}")
        update: dict[str, Any] = {"fact_check_result": result.model_dump(), "fact_checked": result.passed}
        if result.passed:
            update["final_post"] = post
        return update

    def publish(state: ContentState) -> dict[str, Any]:
        # Idempotency: never publish twice for one run.
        if state.get("linkedin_post_id") or state.get("published"):
            return {"published": True, "status": PUBLISHED}
        if not (state.get("approved") and state.get("fact_checked") and state.get("final_post")):
            return _fail(state, "publish", "refusing to publish: checks not passed")
        if s.dry_run:
            log.info("run=%s DRY_RUN: not publishing", state["run_id"])
            return {"status": DRY_RUN_COMPLETE, "published": False}
        if not s.auto_publish:
            return {"status": AWAITING_APPROVAL, "published": False}
        if deps.publisher is None:
            return _fail(state, "publish", "no publisher configured")
        try:
            post_id = deps.publisher.publish(state["final_post"], state["run_id"])
        except Exception as e:  # never blindly retry publishing
            return _fail(state, "publish", f"{type(e).__name__}: {e}")
        return {"published": True, "linkedin_post_id": post_id, "status": PUBLISHED}

    def save_result(state: ContentState) -> dict[str, Any]:
        try:
            deps.repository.save_result(dict(state))
        except Exception as e:
            log.error("run=%s save failed: %s", state.get("run_id"), e)
            return {"errors": [f"save_result: {type(e).__name__}: {e}"]}
        log.info("run=%s saved status=%s", state.get("run_id"), state.get("status"))
        return {}

    return {
        "research": research, "select_topic": select_topic, "build_context": build_context,
        "write_post": write_post, "review_post": review_post, "rewrite_post": rewrite_post,
        "fact_check": fact_check, "publish": publish, "save_result": save_result,
    }
