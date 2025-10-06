from __future__ import annotations

from datetime import datetime

from app.models.article import Article, InferenceResult
from app.models.db import db
from app.services import parsing


def test_api_list_requires_auth(client):
    resp = client.get("/api/articles")
    assert resp.status_code == 401


def test_api_accepts_bearer_token(app, client):
    with app.app_context():
        app.config["API_ACCESS_TOKENS"] = ("test-token",)

    resp = client.get("/api/articles", headers={"Authorization": "Bearer test-token"})
    assert resp.status_code == 200


def test_api_accepts_x_api_key(app, client):
    with app.app_context():
        app.config["API_ACCESS_TOKENS"] = ("token-x",)

    resp = client.get("/api/articles", headers={"X-API-Key": "token-x"})
    assert resp.status_code == 200


def test_api_create_article_success(app, client, auth_header, mocker):
    with app.app_context():
        app.config["ENABLE_AI"] = True

    sample_url = "https://news.yahoo.co.jp/articles/api-success"

    mocker.patch("app.routes.scraping.fetch", return_value=mocker.Mock(url=sample_url, text="html"))
    parsed = parsing.ParsedArticle(url=sample_url, title="APIタイトル", published_at=datetime.utcnow(), body="本文")
    mocker.patch("app.routes.parsing.parse_article", return_value=parsed)
    mocker.patch(
        "app.routes.ai_service.summarize_and_score",
        return_value=mocker.Mock(summary="要約", risk_score=55, model="gpt-test", prompt_version="v1"),
    )

    resp = client.post("/api/articles", json={"url": sample_url}, headers=auth_header)
    data = resp.get_json()

    assert resp.status_code == 201
    assert data["status"] == "created"
    assert data["article"]["title"] == "APIタイトル"
    assert data["ai"]["run"] is True
    assert len(data["article"]["inference_history"]) == 1

    with app.app_context():
        app.config["ENABLE_AI"] = False


def test_api_get_article_not_found(client, auth_header):
    resp = client.get("/api/articles/does-not-exist", headers=auth_header)
    assert resp.status_code == 404


def test_api_create_article_cached(app, client, auth_header, mocker):
    with app.app_context():
        article = Article(
            url="https://news.yahoo.co.jp/articles/api-cached",
            title="既存",
            published_at=None,
            body="本文",
        )
        db.session.add(article)
        db.session.commit()

    resp = client.post(
        "/api/articles",
        json={"url": "https://news.yahoo.co.jp/articles/api-cached"},
        headers=auth_header,
    )

    data = resp.get_json()
    assert resp.status_code == 200
    assert data["status"] == "cached"
    assert data["article"]["inference"] is None


def test_api_create_article_force_update(app, client, auth_header, mocker):
    sample_url = "https://news.yahoo.co.jp/articles/api-force"
    with app.app_context():
        article = Article(
            url=sample_url,
            title="旧タイトル",
            published_at=None,
            body="旧本文",
        )
        db.session.add(article)
        db.session.commit()

    mocker.patch("app.routes.scraping.fetch", return_value=mocker.Mock(url=sample_url, text="html"))
    parsed = parsing.ParsedArticle(url=sample_url, title="新タイトル", published_at=None, body="新本文")
    mocker.patch("app.routes.parsing.parse_article", return_value=parsed)

    resp = client.post(
        "/api/articles",
        json={"url": sample_url, "force": True, "run_ai": False},
        headers=auth_header,
    )

    data = resp.get_json()
    assert resp.status_code == 200
    assert data["status"] == "updated"
    assert data["article"]["title"] == "新タイトル"
    assert data["ai"]["run"] is False
    assert data["article"]["inference_history"] == []


def test_api_rate_limit(app, client, auth_header):
    from app import _RATE_BUCKETS

    with app.app_context():
        app.config["RATE_LIMIT_PER_MINUTE"] = 2

    _RATE_BUCKETS.clear()
    client.get("/api/articles", headers=auth_header)
    client.get("/api/articles", headers=auth_header)
    resp = client.get("/api/articles", headers=auth_header)
    assert resp.status_code == 429
    _RATE_BUCKETS.clear()
    with app.app_context():
        app.config["RATE_LIMIT_PER_MINUTE"] = 1000


def test_api_rate_limit_uses_first_forwarded_ip(app, client, auth_header):
    from app import _RATE_BUCKETS

    with app.app_context():
        app.config["RATE_LIMIT_PER_MINUTE"] = 1

    _RATE_BUCKETS.clear()

    headers_primary = dict(auth_header)
    headers_primary["X-Forwarded-For"] = "1.2.3.4, 5.6.7.8"

    resp1 = client.get("/api/articles", headers=headers_primary)
    assert resp1.status_code == 200

    headers_variant = dict(auth_header)
    headers_variant["X-Forwarded-For"] = "1.2.3.4 ,5.6.7.8"

    resp2 = client.get("/api/articles", headers=headers_variant)
    assert resp2.status_code == 429

    _RATE_BUCKETS.clear()

    with app.app_context():
        app.config["RATE_LIMIT_PER_MINUTE"] = 1000


def test_api_rate_limit_normalizes_api_key(app, client):
    from app import _RATE_BUCKETS

    with app.app_context():
        app.config.update(
            RATE_LIMIT_PER_MINUTE=1,
            API_ACCESS_TOKENS=("token-x",),
        )

    _RATE_BUCKETS.clear()

    resp1 = client.get("/api/articles", headers={"X-API-Key": " token-x "})
    assert resp1.status_code == 200

    resp2 = client.get("/api/articles", headers={"X-API-Key": "token-x"})
    assert resp2.status_code == 429

    _RATE_BUCKETS.clear()

    with app.app_context():
        app.config["RATE_LIMIT_PER_MINUTE"] = 1000


def test_api_list_filters_by_risk(app, client, auth_header):
    with app.app_context():
        high = Article(
            url="https://news.yahoo.co.jp/articles/high-risk",
            title="高リスクAPI",
            published_at=datetime.utcnow(),
            body="本文",
        )
        low = Article(
            url="https://news.yahoo.co.jp/articles/low-risk",
            title="低リスクAPI",
            published_at=datetime.utcnow(),
            body="本文",
        )
        db.session.add_all([high, low])
        db.session.flush()
        db.session.add_all(
            [
                InferenceResult(
                    article_id=high.id,
                    risk_score=88,
                    summary="高",
                    model="gpt",
                    prompt_version="v1",
                ),
                InferenceResult(
                    article_id=low.id,
                    risk_score=25,
                    summary="低",
                    model="gpt",
                    prompt_version="v1",
                ),
            ]
        )
        db.session.commit()

    resp = client.get("/api/articles?risk=high", headers=auth_header)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["total"] == 1
    assert data["items"][0]["title"] == "高リスクAPI"


def test_api_report_summary(app, client, auth_header):
    with app.app_context():
        article = Article(
            url="https://news.yahoo.co.jp/articles/summary",
            title="レポート記事",
            published_at=datetime.utcnow(),
            body="本文",
        )
        db.session.add(article)
        db.session.flush()
        inference = InferenceResult(
            article_id=article.id,
            risk_score=90,
            summary="summary",
            model="gpt",
            prompt_version="v1",
        )
        db.session.add(inference)
        db.session.commit()

    resp = client.get("/api/reports/summary", headers=auth_header)
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["total_articles"] == 1
    assert data["highest_risk"]["risk_score"] == 90
    assert data["risk_distribution"]["high"] == 1
