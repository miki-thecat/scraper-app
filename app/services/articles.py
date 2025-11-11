from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from dateutil import parser as dateparser, tz
from flask import current_app
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import aliased

from app.models.article import Article, InferenceResult
from app.models.db import db

from . import ai as ai_service
from . import parsing, risk, scraping


@dataclass(slots=True)
class ArticleIngestionResult:
    article: Article
    status: Literal["created", "updated", "cached"]
    ai_enabled: bool
    ai_ran: bool
    ai_error: str | None


class ArticleIngestionError(RuntimeError):
    """Domain error raised when ingesting an article fails."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return dateparser.parse(value)
    except (ValueError, TypeError, OverflowError):
        return None


def article_select(
    search_query: str,
    start_date: datetime | None,
    end_date: datetime | None,
    sort_key: str = "published_at",
    order: str = "desc",
    risk_band: risk.RiskBand | None = None,
) -> Select[tuple[Article]]:
    stmt = select(Article)

    if search_query:
        like_pattern = f"%{search_query}%"
        stmt = stmt.where(
            or_(
                Article.title.ilike(like_pattern),
                Article.body.ilike(like_pattern),
            )
        )

    if start_date is not None:
        stmt = stmt.where(Article.published_at >= start_date)
    if end_date is not None:
        stmt = stmt.where(Article.published_at <= end_date)

    if risk_band is not None:
        latest = aliased(InferenceResult)
        latest_subquery = (
            select(InferenceResult.id)
            .where(InferenceResult.article_id == Article.id)
            .order_by(InferenceResult.created_at.desc(), InferenceResult.id.desc())
            .limit(1)
            .scalar_subquery()
        )
        stmt = stmt.join(latest, latest.id == latest_subquery)
        stmt = stmt.where(latest.risk_score >= risk_band.min_score)
        if risk_band.max_score is not None:
            stmt = stmt.where(latest.risk_score <= risk_band.max_score)

    sort_columns = {
        "published_at": Article.published_at,
        "created_at": Article.created_at,
        "title": Article.title,
    }
    column = sort_columns.get(sort_key, Article.published_at)
    direction = column.desc() if order == "desc" else column.asc()

    return stmt.order_by(direction, Article.created_at.desc())


def risk_level_payload(score: int | None) -> dict[str, Any] | None:
    level = risk.classify(score)
    if level is None:
        return None
    return {
        "slug": level.slug,
        "name": level.name,
        "badge": level.badge,
        "description": level.description,
        "min_score": level.min_score,
        "max_score": level.max_score,
    }


def article_to_dict(article: Article) -> dict[str, Any]:
    history = [
        {
            "id": record.id,
            "risk_score": record.risk_score,
            "risk_level": risk_level_payload(record.risk_score),
            "summary": record.summary,
            "model": record.model,
            "prompt_version": record.prompt_version,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
        for record in article.inferences
    ]
    return {
        "id": article.id,
        "url": article.url,
        "title": article.title,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "body": article.body,
        "created_at": article.created_at.isoformat() if article.created_at else None,
        "inference": history[0] if history else None,
        "inference_history": history,
        "risk_level": risk_level_payload(article.latest_inference.risk_score) if article.latest_inference else None,
    }


def ingest_article(
    url: str,
    *,
    force: bool = False,
    run_ai: bool = True,
    force_ai: bool = False,
) -> ArticleIngestionResult:
    """Fetch, parse, persist, and optionally run AI for a Yahoo!ニュース article."""

    if not url:
        raise ArticleIngestionError("URLを指定してください。", status_code=400)
    if not scraping.is_allowed(url):
        raise ArticleIngestionError("Yahoo!ニュースの記事URLのみ対応しています。", status_code=400)

    article = db.session.scalar(select(Article).where(Article.url == url))
    needs_fetch = force or article is None
    parsed = None
    status: Literal["created", "updated", "cached"] = "cached"

    if needs_fetch:
        try:
            response = scraping.fetch(url)
            parsed = parsing.parse_article(response.url, response.text)
        except scraping.ScrapeError as exc:
            db.session.rollback()
            current_app.logger.warning("Scraping failed for %s: %s", url, exc)
            raise ArticleIngestionError(str(exc), status_code=502) from exc
        except parsing.ParseError as exc:
            db.session.rollback()
            current_app.logger.warning("Parsing failed for %s: %s", url, exc)
            raise ArticleIngestionError("記事の本文を解析できませんでした。", status_code=422) from exc

        if article is None:
            article = Article(
                url=parsed.url,
                title=parsed.title,
                published_at=parsed.published_at,
                body=parsed.body,
            )
            db.session.add(article)
            status = "created"
        else:
            article.url = parsed.url
            article.title = parsed.title
            article.published_at = parsed.published_at
            article.body = parsed.body
            status = "updated"

    db.session.flush()

    ai_enabled = current_app.config.get("ENABLE_AI", True)
    ai_ran = False
    ai_error: str | None = None

    latest = article.latest_inference

    if run_ai and ai_enabled and (force_ai or latest is None or needs_fetch):
        try:
            ai_result = ai_service.summarize_and_score(article.title, article.body[:4000])
        except ai_service.AIServiceUnavailable as exc:
            ai_error = str(exc)
        else:
            inference = InferenceResult(
                article_id=article.id,
                risk_score=ai_result.risk_score,
                summary=ai_result.summary,
                model=ai_result.model,
                prompt_version=ai_result.prompt_version,
            )
            db.session.add(inference)
            ai_ran = True

    db.session.commit()

    return ArticleIngestionResult(
        article=article,
        status=status,
        ai_enabled=ai_enabled,
        ai_ran=ai_ran,
        ai_error=ai_error,
    )


def format_timestamp(dt: datetime | None) -> str | None:
    """Utility for CLI/UI to show timestamps in JST."""
    if dt is None:
        return None
    tokyo = tz.gettz("Asia/Tokyo")
    try:
        return dt.astimezone(tokyo).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        return None
