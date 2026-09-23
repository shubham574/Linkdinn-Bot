# linkedin-agent (Phase 1)

LangGraph pipeline: research → select_topic → build_context → write → review ⇄ rewrite → fact_check → publish → save.
Phase 1 ships the scaffold, config, DB + migration, typed state, routing (with revision cap), and stub agents.

## Run locally
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    python -m app.run                 # dry run with stub agents (SQLite)
    python -m app.run --date 2026-09-23
    pytest

## Postgres + migrations
    docker compose up -d db
    # set DATABASE_URL=postgresql+psycopg://linkedin:linkedin@localhost:5432/linkedin_agent in .env
    alembic upgrade head

## Safety
DRY_RUN=true and AUTO_PUBLISH=false by default. Publishing requires approved + fact_checked + DRY_RUN=false + AUTO_PUBLISH=true.
Failed or capped runs end as `manual_review_required` and are never published.

## Known limitations (Phase 1)
Agents are stubs; no LinkedIn publisher, scheduler, API, or duplicate detection yet.
