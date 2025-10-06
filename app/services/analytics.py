"""ダッシュボード用の集計処理。"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, func, select

from app.models.article import Article, InferenceResult
from app.services import risk


@dataclass(slots=True)
class DashboardMetrics:
    total_articles: int
    ai_coverage_ratio: float
    high_risk_articles: int
    average_risk_score: float
    highest_risk_title: str | None
    highest_risk_score: int | None
    highest_risk_article_id: str | None
    risk_distribution: dict[str, int]


def gather_metrics(session) -> DashboardMetrics:
    """記事・AI推論の状態を集計して可視化用メトリクスを返す。"""

    total_articles = session.scalar(select(func.count(Article.id))) or 0

    inference_count = session.scalar(select(func.count(InferenceResult.id))) or 0
    high_risk_articles = (
        session.scalar(
            select(func.count(InferenceResult.id)).where(InferenceResult.risk_score >= 70)
        )
        or 0
    )

    average_risk_score = session.scalar(select(func.avg(InferenceResult.risk_score))) or 0.0

    # 最新の推論結果を抽出してリスク分布を集計
    windowed = (
        select(
            InferenceResult.article_id.label("article_id"),
            InferenceResult.risk_score.label("risk_score"),
            func.row_number()
            .over(
                partition_by=InferenceResult.article_id,
                order_by=(
                    InferenceResult.created_at.desc(),
                    InferenceResult.id.desc(),
                ),
            )
            .label("rn"),
        )
    ).subquery()

    latest_scores = session.execute(
        select(windowed.c.risk_score).where(windowed.c.rn == 1)
    ).scalars()

    risk_distribution = {band.slug: 0 for band in risk.levels()}
    for score in latest_scores:
        band = risk.classify(int(score) if score is not None else None)
        if band:
            risk_distribution[band.slug] += 1

    highest_risk_row = session.execute(_highest_risk_query()).first()
    if highest_risk_row:
        highest_risk_article_id, highest_risk_title, highest_risk_score = highest_risk_row
    else:
        highest_risk_article_id, highest_risk_title, highest_risk_score = None, None, None

    ai_coverage_ratio = 0.0
    if total_articles:
        ai_coverage_ratio = round(min(1.0, inference_count / total_articles), 3)

    return DashboardMetrics(
        total_articles=total_articles,
        ai_coverage_ratio=ai_coverage_ratio,
        high_risk_articles=high_risk_articles,
        average_risk_score=round(average_risk_score, 1) if average_risk_score else 0.0,
        highest_risk_title=highest_risk_title,
        highest_risk_score=int(highest_risk_score) if highest_risk_score is not None else None,
        highest_risk_article_id=highest_risk_article_id,
        risk_distribution=risk_distribution,
    )


def _highest_risk_query() -> Select:
    return (
        select(Article.id, Article.title, InferenceResult.risk_score)
        .join(InferenceResult, InferenceResult.article_id == Article.id)
        .order_by(InferenceResult.risk_score.desc(), InferenceResult.created_at.desc())
        .limit(1)
    )
