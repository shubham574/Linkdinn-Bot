"""SQLAlchemy models + repository. Postgres in production; SQLite works for local/tests."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint, create_engine, select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    linkedin_member_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WritingProfile(Base):
    __tablename__ = "writing_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    profile_text: Mapped[str] = mapped_column(Text, default="")
    style_rules: Mapped[dict | list | None] = mapped_column(JSONType)
    topics: Mapped[dict | list | None] = mapped_column(JSONType)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class StyleExample(Base):
    __tablename__ = "style_examples"
    __table_args__ = (
        CheckConstraint("label IN ('preferred','neutral','avoid')", name="ck_style_label"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(200))
    label: Mapped[str] = mapped_column(String(20), default="neutral")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ResearchRun(Base):
    __tablename__ = "research_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    topic: Mapped[str | None] = mapped_column(String(500))
    research_summary: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list | None] = mapped_column(JSONType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Post(Base):
    __tablename__ = "posts"
    # unique run_id = one post per run (idempotency guard at the DB level)
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_posts_run_id"),
        Index("ix_posts_status_created", "status", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64))
    topic: Mapped[str | None] = mapped_column(String(500))
    draft: Mapped[str | None] = mapped_column(Text)
    final_post: Mapped[str | None] = mapped_column(Text)
    review_result: Mapped[dict | None] = mapped_column(JSONType)
    fact_check_result: Mapped[dict | None] = mapped_column(JSONType)
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40))
    errors: Mapped[list | None] = mapped_column(JSONType)
    linkedin_post_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Topic(Base):
    __tablename__ = "topics"
    id: Mapped[int] = mapped_column(primary_key=True)
    topic: Mapped[str] = mapped_column(String(500), unique=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    times_rejected: Mapped[int] = mapped_column(Integer, default=0)


class PostMetric(Base):
    """Prepared for future LinkedIn analytics (not populated in v1)."""

    __tablename__ = "post_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    impressions: Mapped[int | None] = mapped_column(Integer)
    likes: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[int | None] = mapped_column(Integer)
    reposts: Mapped[int | None] = mapped_column(Integer)
    clicks: Mapped[int | None] = mapped_column(Integer)
    engagement_rate: Mapped[float | None] = mapped_column(Float)
    raw: Mapped[dict | None] = mapped_column(JSONType)


def make_session_factory(database_url: str) -> sessionmaker[Session]:
    kwargs: dict[str, Any] = {}
    if database_url.startswith("sqlite") and ":memory:" in database_url:
        from sqlalchemy.pool import StaticPool
        kwargs = {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
    engine = create_engine(database_url, **kwargs)
    return sessionmaker(engine, expire_on_commit=False)


class PostRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._sf = session_factory

    def create_all(self) -> None:
        """Dev/test convenience. Production uses Alembic migrations."""
        Base.metadata.create_all(self._sf.kw["bind"])

    def save_result(self, state: dict[str, Any]) -> None:
        topic = (state.get("selected_topic") or {}).get("title")
        status = state.get("status", "unknown")
        with self._sf() as s, s.begin():
            post = s.scalar(select(Post).where(Post.run_id == state["run_id"]))
            if post is None:
                post = Post(run_id=state["run_id"])
                s.add(post)
            post.topic = topic
            post.draft = state.get("draft_post")
            post.final_post = state.get("final_post") or state.get("revised_post")
            post.review_result = state.get("review_result")
            post.fact_check_result = state.get("fact_check_result")
            post.revision_count = state.get("revision_count", 0)
            post.status = status
            post.errors = state.get("errors") or []
            if state.get("linkedin_post_id"):
                post.linkedin_post_id = state["linkedin_post_id"]
                post.published_at = post.published_at or utcnow()

            if topic and state.get("research_sources") is not None:
                s.add(ResearchRun(
                    run_id=state["run_id"], topic=topic,
                    research_summary=state.get("research_summary"),
                    sources=state.get("research_sources"),
                ))
            if topic:
                row = s.scalar(select(Topic).where(Topic.topic == topic))
                if row is None:
                    row = Topic(topic=topic, usage_count=0, times_rejected=0)
                    s.add(row)
                if status in ("published", "dry_run_complete", "awaiting_approval"):
                    row.usage_count = (row.usage_count or 0) + 1
                    row.last_used = utcnow()
                else:
                    row.times_rejected = (row.times_rejected or 0) + 1

    def get_post(self, run_id: str) -> Post | None:
        with self._sf() as s:
            return s.scalar(select(Post).where(Post.run_id == run_id))

    def previous_topics(self) -> list[str]:
        with self._sf() as s:
            return list(s.scalars(select(Topic.topic)))
