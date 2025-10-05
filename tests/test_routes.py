from __future__ import annotations

from datetime import datetime

from app.models.article import Article, InferenceResult
from app.services import parsing
from app.models.db import db


def test_index_requires_auth(client):
    resp = client.get("/")
    assert resp.status_code == 401


def test_index_with_auth_lists_articles(app, client, auth_header):
    with app.app_context():
        article = Article(
            url="https://news.yahoo.co.jp/articles/with-auth",
            title="一覧表示用",
            published_at=None,
            body="本文テスト",
        )
        db.session.add(article)
        db.session.commit()

        article_id = article.id

    resp = client.get("/", headers=auth_header)
    assert resp.status_code == 200
    assert "一覧表示用" in resp.get_data(as_text=True)
    assert str(article_id) in resp.get_data(as_text=True)


def test_scrape_creates_article(app, client, auth_header, mocker):
    url = "https://news.yahoo.co.jp/articles/example"
    parsed = parsing.ParsedArticle(url=url, title="タイトル", published_at=datetime.utcnow(), body="本文")
    mocker.patch("app.routes.scraping.is_allowed", return_value=True)
    mocker.patch("app.routes.scraping.fetch", return_value=mocker.Mock(url=url, text="html"))
    mocker.patch("app.routes.parsing.parse_article", return_value=parsed)

    resp = client.post("/scrape", data={"url": url}, headers=auth_header, follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        article = Article.query.filter_by(url=url).first()
        assert article is not None
        assert article.title == "タイトル"


def test_scrape_reuses_existing_article(app, client, auth_header):
    with app.app_context():
        article = Article(url="https://news.yahoo.co.jp/articles/existing", title="旧", published_at=None, body="本文")
        db.session.add(article)
        db.session.commit()

        article_id = article.id

    resp = client.post(
        "/scrape",
        data={"url": "https://news.yahoo.co.jp/articles/existing"},
        headers=auth_header,
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert str(article_id) in resp.headers["Location"]


def test_result_page_displays_article(app, client, auth_header):
    with app.app_context():
        article = Article(
            url="https://news.yahoo.co.jp/articles/detail",
            title="詳細ページ",
            published_at=None,
            body="段落1\n\n段落2",
        )
        db.session.add(article)
        db.session.commit()
        article_id = article.id

    resp = client.get(f"/result/{article_id}", headers=auth_header)
    text = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "詳細ページ" in text
    assert "段落1" in text
    assert "段落2" in text


def test_result_ai_page_displays_inference(app, client, auth_header):
    with app.app_context():
        article = Article(
            url="https://news.yahoo.co.jp/articles/ai",
            title="AIページ",
            published_at=None,
            body="本文",
        )
        db.session.add(article)
        db.session.flush()

        inference = InferenceResult(
            article_id=article.id,
            risk_score=88,
            summary="要約1\n要約2",
            model="gpt-4o-mini",
            prompt_version="v1",
        )
        db.session.add(inference)
        db.session.commit()
        article_id = article.id

    resp = client.get(f"/result_ai/{article_id}", headers=auth_header)
    text = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "リスクスコア" in text
    assert "88" in text
    assert "要約1" in text and "要約2" in text
