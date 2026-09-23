from app.graph.state import MANUAL_REVIEW, ContentState


def _halted(state: ContentState) -> bool:
    return state.get("status") == MANUAL_REVIEW


def proceed_or_save(next_node: str):
    """Generic router: any node that flagged manual review short-circuits to save_result."""

    def route(state: ContentState) -> str:
        return "save_result" if _halted(state) else next_node

    return route


def route_after_review(state: ContentState) -> str:
    if _halted(state):
        return "save_result"
    if state.get("approved"):
        return "fact_check"
    if state.get("revision_count", 0) >= state.get("max_revisions", 0):
        return "mark_manual"
    return "rewrite_post"


def route_after_fact_check(state: ContentState) -> str:
    if _halted(state):
        return "save_result"
    if state.get("fact_checked"):
        return "publish"
    if state.get("revision_count", 0) >= state.get("max_revisions", 0):
        return "mark_manual"
    return "rewrite_post"
