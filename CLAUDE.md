# linkedin-agent — working notes for Claude Code

Decisions (override the original spec where they differ):
- Gemini API: research, writing, rewriting, fact-checking. Laya (convaiinnovations/laya): topic scoring + post "humanness" rating. NO "JEV".
- Laya only outputs typed decisions (choice/score/noul); it never generates text. Base checkpoints are near chance until fine-tuned.
- Graph depends only on Protocols in app/agents/base.py. Swap implementations, don't edit the graph.
- Safety defaults: DRY_RUN=true, AUTO_PUBLISH=false. Never publish on failed checks; never invent personal experiences.
- Verify LinkedIn Posts API docs before Phase 5; keep API version configurable.

Phases: 1 scaffold (DONE) · 2 Gemini research/topic/writer · 3 Laya rater + rewrite loop · 4 fact-check, dup detection, memory
· 5 LinkedIn OAuth/publisher · 6 scheduler, FastAPI, logging · 7 tests/deploy. Run `pytest` before moving on.
