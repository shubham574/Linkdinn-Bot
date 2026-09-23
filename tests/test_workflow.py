import pytest
from pydantic import ValidationError

from app.agents.base import PostRating
from app.config import Settings
from app.services.content_service import evaluate_approval
from app.tools.database import PostRepository, make_session_factory
from tests.conftest import initial, rating

S = Settings(_env_file=None)


def test_approval_passes_good_rating():
    assert evaluate_approval(rating(True), S).approved


@pytest.mark.parametrize("field,value", [
    ("human_naturalness", 84), ("personal_voice", 10), ("specificity", 10),
    ("factual_confidence", 50), ("generic_ai_language", 90), ("fabricated_personal_claim_prob", 0.5),
])
def test_each_criterion_can_fail_alone(field, value):
    d = evaluate_approval(rating(True, **{field: value}), S)
    assert not d.approved and len(d.failed_criteria) == 1


def test_thresholds_are_configurable():
    assert evaluate_approval(rating(True, human_naturalness=80), Settings(_env_file=None, rater_approval_threshold=75)).approved


def test_invalid_model_output_rejected():
    with pytest.raises(ValidationError):
        PostRating(human_naturalness=150)


def test_db_persistence_and_run_idempotency(make_graph):
    repo = PostRepository(make_session_factory("sqlite:///:memory:"))
    repo.create_all()
    graph, _ = make_graph(repo=repo)
    out = graph.invoke(initial("run-x"))
    graph.invoke({**initial("run-x")})  # same run_id again -> upsert, not a second row
    post = repo.get_post("run-x")
    assert post.status == out["status"] == "dry_run_complete"
    assert post.final_post and post.review_result["approved"] is True
    assert repo.previous_topics() == ["Stub topic A"]
