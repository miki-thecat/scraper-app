from __future__ import annotations

from datetime import datetime, timezone

from app.models.article import Article, InferenceResult
from app.models.db import db
from app.services import analytics


def test_gather_metrics(app):
    with app.app_context():
        article1 = Article(
            url="https://news.yahoo.co.jp/articles/portfolio-1",
            title="テスト記事1",
            published_at=datetime.now(timezone.utc),
            body="本文1",
        )
        article2 = Article(
            url="https://news.yahoo.co.jp/articles/portfolio-2",
            title="テスト記事2",
            published_at=datetime.now(timezone.utc),
            body="本文2",
        )
        db.session.add_all([article1, article2])
        db.session.flush()

        inference1 = InferenceResult(
            article_id=article1.id,
            risk_score=80,
            summary="summary",
            model="gpt-test",
            prompt_version="v1",
        )
        inference2 = InferenceResult(
            article_id=article2.id,
            risk_score=40,
            summary="summary",
            model="gpt-test",
            prompt_version="v1",
        )
        db.session.add_all([inference1, inference2])
        db.session.commit()

        metrics = analytics.gather_metrics(db.session)

        assert metrics.total_articles == 2
        assert metrics.high_risk_articles == 1
        assert metrics.highest_risk_score == 80
        assert metrics.highest_risk_article_id == article1.id
        assert metrics.ai_coverage_ratio == 1.0
        assert metrics.risk_distribution["high"] == 1
        assert metrics.risk_distribution["moderate"] == 1
