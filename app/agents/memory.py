from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.agents.base import MemoryStore
from app.tools.database import Post, Topic, WritingProfile


class SQLMemoryStore:
    """SQLAlchemy implementation of the MemoryStore protocol."""

    def __init__(self, session_factory: sessionmaker[Session]):
        self._sf = session_factory

    def previous_topics(self) -> list[str]:
        with self._sf() as s:
            return list(s.scalars(select(Topic.topic)))

    def personal_context(self, topic: dict[str, Any]) -> list[dict[str, Any]]:
        # In a real system, you might filter context based on the topic.
        # Here we return the writing profile text and style rules.
        with self._sf() as s:
            profile = s.scalar(select(WritingProfile).limit(1))
            if not profile:
                return []
            
            return [{
                "profile_text": profile.profile_text,
                "style_rules": profile.style_rules,
                "topics": profile.topics
            }]

    def previous_posts(self, topic: dict[str, Any]) -> list[dict[str, Any]]:
        # Retrieve posts that have been published or drafted to avoid repeating.
        with self._sf() as s:
            posts = s.scalars(
                select(Post).where(Post.status.in_(["published", "draft"]))
                .order_by(Post.created_at.desc())
                .limit(5)
            ).all()
            
            return [{
                "topic": p.topic,
                "final_post": p.final_post,
                "linkedin_post_id": p.linkedin_post_id,
            } for p in posts if p.final_post]

