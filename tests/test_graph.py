from tests.conftest import (
    EmptyResearcher, NoSourcesResearcher, RecordingPublisher, ScriptedFactChecker,
    ScriptedRater, initial, rating,
)


def test_happy_path_dry_run_never_publishes(make_graph):
    pub = RecordingPublisher()
    graph, repo = make_graph(publisher=pub)  # defaults: dry_run=True
    out = graph.invoke(initial())
    assert out["status"] == "dry_run_complete"
    assert out["final_post"] and out["published"] is False
    assert pub.calls == [] and len(repo.saved) == 1


def test_reject_then_rewrite_then_approve(make_graph):
    rater = ScriptedRater([rating(False), rating(True)])
    graph, _ = make_graph(rater=rater)
    out = graph.invoke(initial())
    assert out["revision_count"] == 1 and rater.calls == 2
    assert out["status"] == "dry_run_complete"
    assert out["final_post"].endswith("(revised)")


def test_revision_limit_stops_loop_and_never_publishes(make_graph):
    pub = RecordingPublisher()
    rater = ScriptedRater([rating(False)])
    graph, repo = make_graph(rater=rater, publisher=pub, dry_run=False, auto_publish=True, max_revisions=3)
    out = graph.invoke(initial())
    assert out["status"] == "manual_review_required"
    assert out["revision_count"] == 3 and rater.calls == 4
    assert pub.calls == [] and not out.get("final_post")
    assert repo.saved[0]["review_result"]["failed_criteria"]  # feedback kept


def test_fact_check_failure_routes_through_rewrite_and_rereview(make_graph):
    rater, fact = ScriptedRater([rating()]), ScriptedFactChecker([False, True])
    graph, _ = make_graph(rater=rater, fact=fact)
    out = graph.invoke(initial())
    assert fact.calls == 2 and rater.calls == 2 and out["revision_count"] == 1
    assert out["status"] == "dry_run_complete"


def test_fact_check_always_fails_is_capped(make_graph):
    pub = RecordingPublisher()
    fact = ScriptedFactChecker([False])
    graph, _ = make_graph(fact=fact, publisher=pub, dry_run=False, auto_publish=True, max_revisions=2)
    out = graph.invoke(initial())
    assert out["status"] == "manual_review_required" and pub.calls == []
    assert fact.calls == 3


def test_auto_publish_publishes_once_and_records_id(make_graph):
    pub = RecordingPublisher()
    graph, repo = make_graph(publisher=pub, dry_run=False, auto_publish=True)
    out = graph.invoke(initial())
    assert out["status"] == "published" and out["linkedin_post_id"] == "urn:li:share:123"
    assert len(pub.calls) == 1 and repo.saved[0]["linkedin_post_id"] == "urn:li:share:123"


def test_manual_approval_mode_waits(make_graph):
    pub = RecordingPublisher()
    graph, _ = make_graph(publisher=pub, dry_run=False, auto_publish=False)
    assert graph.invoke(initial())["status"] == "awaiting_approval" and pub.calls == []


def test_publisher_error_is_not_retried(make_graph):
    pub = RecordingPublisher(fail=True)
    graph, _ = make_graph(publisher=pub, dry_run=False, auto_publish=True)
    out = graph.invoke(initial())
    assert out["status"] == "manual_review_required" and len(pub.calls) == 1


def test_empty_research_halts_before_writing(make_graph):
    graph, repo = make_graph(researcher=EmptyResearcher())
    out = graph.invoke(initial())
    assert out["status"] == "manual_review_required" and "draft_post" not in out
    assert len(repo.saved) == 1


def test_missing_sources_blocks(make_graph):
    graph, _ = make_graph(researcher=NoSourcesResearcher())
    assert graph.invoke(initial())["status"] == "manual_review_required"


def test_invalid_rater_output_halts_safely(make_graph):
    pub = RecordingPublisher()
    graph, _ = make_graph(rater=ScriptedRater([ValueError("bad json")]), publisher=pub,
                          dry_run=False, auto_publish=True)
    out = graph.invoke(initial())
    assert out["status"] == "manual_review_required" and pub.calls == []
    assert any("invalid rater output" in e for e in out["errors"])


def test_high_average_cannot_hide_fabricated_claim(make_graph):
    graph, _ = make_graph(rater=ScriptedRater([rating(fabricated_personal_claim_prob=0.9)]), max_revisions=1)
    out = graph.invoke(initial())
    assert out["status"] == "manual_review_required"
