"""Manual execution:  python -m app.run [--date YYYY-MM-DD]"""
import argparse
import json
import logging
import uuid
from datetime import date

from app.agents import stubs
from app.agents.gemini import GeminiResearcher, GeminiWriter, GeminiRewriter, GeminiFactChecker
from app.agents.laya_agents import LayaTopicSelector, LayaPostRater
from app.agents.memory import SQLMemoryStore
from app.agents.publisher import LinkedInPublisher
from app.config import get_settings
from app.graph.nodes import Deps
from app.graph.workflow import build_workflow
from app.tools.database import PostRepository, make_session_factory


def build_deps(settings, repository) -> Deps:
    # Phase 2-4 swap these stubs for Gemini / Laya implementations.
    return Deps(
        settings=settings,
        researcher=GeminiResearcher(settings),
        selector=LayaTopicSelector(settings),
        memory=SQLMemoryStore(repository._sf),
        writer=GeminiWriter(settings),
        rewriter=GeminiRewriter(settings),
        rater=LayaPostRater(settings),
        fact_checker=GeminiFactChecker(settings),
        repository=repository,
        publisher=LinkedInPublisher(settings),
    )


def run_once(target_date: str | None = None) -> dict:
    settings = get_settings()
    repo = PostRepository(make_session_factory(settings.database_url))
    if settings.app_env == "development":
        repo.create_all()
    graph = build_workflow(build_deps(settings, repo))
    return graph.invoke({
        "run_id": uuid.uuid4().hex,
        "target_date": target_date or date.today().isoformat(),
        "errors": [], "status": "running",
    })


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=None)
    args = p.parse_args()
    result = run_once(args.date)
    print(json.dumps({k: result.get(k) for k in
                      ("run_id", "status", "selected_topic", "final_post", "revision_count", "errors")},
                     indent=2, default=str))


if __name__ == "__main__":
    main()
