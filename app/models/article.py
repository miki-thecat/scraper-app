from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import db


class Article(db.Model):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    url: Mapped[str] = mapped_column(db.String(512), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(db.Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(db.DateTime(timezone=True))
    body: Mapped[str] = mapped_column(db.Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    inferences: Mapped[list["InferenceResult"]] = relationship(
        "InferenceResult",
        back_populates="article",
        cascade="all, delete-orphan",
        order_by=lambda: (
            InferenceResult.created_at.desc(),
            InferenceResult.id.desc(),
        ),
    )

    @property
    def latest_inference(self) -> "InferenceResult | None":
        if not self.inferences:
            return None
        return max(
            self.inferences,
            key=lambda record: (
                record.created_at or datetime.min,
                record.id,
            ),
        )

    def __repr__(self) -> str:  # pragma: no cover - デバッグ用
        return f"<Article {self.id} {self.title[:20]!r}>"


class InferenceResult(db.Model):
    __tablename__ = "inference_results"

    id: Mapped[str] = mapped_column(
        db.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    article_id: Mapped[str] = mapped_column(
        db.String(36), db.ForeignKey("articles.id"), nullable=False, index=True
    )
    risk_score: Mapped[int] = mapped_column(db.Integer, nullable=False)
    summary: Mapped[str] = mapped_column(db.Text, nullable=False)
    model: Mapped[str] = mapped_column(db.String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(db.String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    article: Mapped[Article] = relationship("Article", back_populates="inferences")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<InferenceResult {self.id} score={self.risk_score}>"
