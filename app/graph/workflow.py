from langgraph.graph import END, START, StateGraph

from app.graph.edges import proceed_or_save, route_after_fact_check, route_after_review
from app.graph.nodes import Deps, build_nodes
from app.graph.state import MANUAL_REVIEW, ContentState


def build_workflow(deps: Deps):
    nodes = build_nodes(deps)
    g = StateGraph(ContentState)
    for name, fn in nodes.items():
        g.add_node(name, fn)

    # Reached when the revision limit is exhausted: never publish, keep draft + feedback.
    def mark_manual(state: ContentState) -> dict:
        return {"status": MANUAL_REVIEW,
                "errors": [f"revision limit ({state.get('max_revisions')}) reached without passing checks"]}

    g.add_node("mark_manual", mark_manual)

    g.add_edge(START, "research")
    for src, nxt in [("research", "select_topic"), ("select_topic", "build_context"),
                     ("build_context", "write_post"), ("write_post", "review_post"),
                     ("rewrite_post", "review_post")]:
        g.add_conditional_edges(src, proceed_or_save(nxt), {nxt: nxt, "save_result": "save_result"})

    g.add_conditional_edges("review_post", route_after_review, {
        "fact_check": "fact_check", "rewrite_post": "rewrite_post",
        "mark_manual": "mark_manual", "save_result": "save_result"})
    g.add_conditional_edges("fact_check", route_after_fact_check, {
        "publish": "publish", "rewrite_post": "rewrite_post",
        "mark_manual": "mark_manual", "save_result": "save_result"})
    g.add_edge("mark_manual", "save_result")
    g.add_edge("publish", "save_result")
    g.add_edge("save_result", END)
    return g.compile()
