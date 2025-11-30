from __future__ import annotations

import io
from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np

from app.models.article import Article, InferenceResult
from app.models.db import db
from app.services import news_feed
from cli import classify_industry


def test_load_artifacts_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(classify_industry, "VECTOR_PATH", tmp_path / "vec.joblib")
    monkeypatch.setattr(classify_industry, "MODEL_PATH", tmp_path / "model.joblib")

    try:
        classify_industry.load_artifacts()
    except FileNotFoundError:
        return
    raise AssertionError("Expected FileNotFoundError when artifacts are missing")


def test_main_predicts_and_prints(monkeypatch, capsys):
    class DummyVectorizer:
        def transform(self, texts):
            return np.array(texts)

    class DummyModel:
        def predict(self, features):
            return np.array(["IT" for _ in features])

        def predict_proba(self, features):
            return np.array([[0.9, 0.1] for _ in features])

    monkeypatch.setattr(
        classify_industry,
        "load_artifacts",
        lambda: (DummyVectorizer(), DummyModel()),
    )

    monkeypatch.setattr(classify_industry.sys, "stdin", io.StringIO("クラウドサービス概要"))

    exit_code = classify_industry.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "予測業界: IT" in captured.out
    assert "0.90" in captured.out


def test_flask_cli_scrape_feed_invokes_ingest(app, mocker):
    runner = app.test_cli_runner()
    feed_items = [
        news_feed.NewsFeedItem(
            title="フィード記事",
            url="https://news.yahoo.co.jp/articles/feed-cli",
            published_at=datetime.now(timezone.utc),
            source="Yahoo!",
            provider="yahoo",
        )
    ]

    def fake_fetch(limit, provider):
        assert provider == "yahoo"
        return feed_items

    mocker.patch("app.cli.news_feed.fetch_latest_articles", side_effect=fake_fetch)
    ingest_mock = mocker.patch(
        "app.cli.article_service.ingest_article",
        return_value=SimpleNamespace(status="created", ai_error=None),
    )

    result = runner.invoke(args=["scrape", "feed", "--limit", "1"])

    assert result.exit_code == 0
    ingest_mock.assert_called_once_with(
        feed_items[0].url,
        force=False,
        run_ai=True,
        force_ai=False,
    )
    assert "created" in result.output


def test_flask_cli_scrape_feed_with_provider_option(app, mocker):
    runner = app.test_cli_runner()
    feed_items = [
        news_feed.NewsFeedItem(
            title="フィード記事",
            url="https://news.nifty.com/articles/feed-cli",
            published_at=datetime.now(timezone.utc),
            source="ニフティ",
            provider="nifty",
        )
    ]

    mocker.patch(
        "app.cli.news_feed.fetch_latest_articles",
        side_effect=lambda limit, provider: feed_items if provider == "nifty" else [],
    )
    ingest_mock = mocker.patch(
        "app.cli.article_service.ingest_article",
        return_value=SimpleNamespace(status="created", ai_error=None),
    )

    result = runner.invoke(args=["scrape", "feed", "--provider", "nifty", "--limit", "1"])
    assert result.exit_code == 0
    ingest_mock.assert_called_once()


def test_flask_cli_ai_rerun_uses_service(app, mocker):
    runner = app.test_cli_runner()
    with app.app_context():
        article = Article(
            url="https://news.yahoo.co.jp/articles/cli-rerun",
            title="CLI再実行",
            published_at=None,
            body="本文",
        )
        db.session.add(article)
        db.session.flush()
        inference = InferenceResult(
            article_id=article.id,
            risk_score=30,
            summary="古い要約",
            model="gpt",
            prompt_version="v1",
        )
        db.session.add(inference)
        db.session.commit()

    stub_article = SimpleNamespace(
        title="CLI再実行",
        latest_inference=SimpleNamespace(risk_score=42),
    )
    mocker.patch(
        "app.cli.article_service.ingest_article",
        return_value=SimpleNamespace(
            status="cached",
            ai_enabled=True,
            ai_error=None,
            ai_ran=True,
            article=stub_article,
        ),
    )

    result = runner.invoke(args=["ai", "rerun", "--limit", "1"])

    assert result.exit_code == 0
    assert "CLI再実行" in result.output


def test_flask_cli_export_csv_stdout(app, mocker):
    runner = app.test_cli_runner()
    with app.app_context():
        article = Article(
            url="https://news.yahoo.co.jp/articles/cli-export",
            title="CLIエクスポート",
            published_at=datetime.now(timezone.utc),
            body="本文",
        )
        db.session.add(article)
        db.session.flush()
        inference = InferenceResult(
            article_id=article.id,
            risk_score=60,
            summary="要約",
            model="gpt",
            prompt_version="v1",
        )
        db.session.add(inference)
        db.session.commit()

    result = runner.invoke(args=["export", "csv", "--output", "-"])

    assert result.exit_code == 0
    assert "CLIエクスポート" in result.output
