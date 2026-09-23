import operator
from typing import Annotated, Any, TypedDict

# Terminal / intermediate run statuses
RUNNING = "running"
PUBLISHED = "published"
DRY_RUN_COMPLETE = "dry_run_complete"
AWAITING_APPROVAL = "awaiting_approval"
MANUAL_REVIEW = "manual_review_required"


class ContentState(TypedDict, total=False):
    run_id: str
    target_date: str

    candidate_topics: list[dict[str, Any]]
    selected_topic: dict[str, Any]
    rejected_topics: list[dict[str, Any]]

    research_results: list[dict[str, Any]]
    research_summary: str
    research_sources: list[dict[str, Any]]

    personal_context: list[dict[str, Any]]
    relevant_previous_posts: list[dict[str, Any]]

    draft_post: str
    revised_post: str
    final_post: str

    review_result: dict[str, Any]
    fact_check_result: dict[str, Any]

    revision_count: int
    max_revisions: int

    approved: bool
    fact_checked: bool
    published: bool

    linkedin_post_id: str | None

    errors: Annotated[list[str], operator.add]
    status: str


def current_post(state: ContentState) -> str:
    """The latest candidate text (revision if one exists, else the draft)."""
    return state.get("revised_post") or state.get("draft_post") or ""
