from __future__ import annotations

from datetime import datetime

from app.models.article import Article
from app.models.db import db
from app.services import parsing


def test_api_list_requires_auth(client):
    resp = client.get("/api/articles")
    assert resp.status_code == 401


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
