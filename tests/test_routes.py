from __future__ import annotations

from datetime import datetime, timezone

from app.models.article import Article, InferenceResult
from app.services import parsing
from app.models.db import db
from app.services.scraping import ScrapeError
from app.services import news_feed


def test_index_requires_auth(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["Location"].startswith("/login")


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
    assert "タイトル・本文を検索" in resp.get_data(as_text=True)


def test_index_renders_latest_feed(app, client, auth_header, mocker):
    feed_items = [
        news_feed.NewsFeedItem(
            title="最新記事",
            url="https://news.yahoo.co.jp/articles/latest",
            published_at=datetime.now(timezone.utc),
            source="Yahoo!ニュース - テック",
        )
    ]

    mocker.patch("app.routes.news_feed.fetch_latest_articles", return_value=feed_items)

    resp = client.get("/", headers=auth_header)
    text = resp.get_data(as_text=True)
    assert "最新のYahoo!ニュースから選ぶ" in text
    assert "最新記事" in text
    assert "AI解析する" in text


def test_export_csv_returns_articles(app, client, auth_header):
    with app.app_context():
        article = Article(
            url="https://news.yahoo.co.jp/articles/export",
            title="エクスポート対象",
            published_at=datetime.now(timezone.utc),
            body="本文",
        )
        db.session.add(article)
        db.session.flush()
        inference = InferenceResult(
            article_id=article.id,
            risk_score=82,
            summary="summary",
            model="gpt",
            prompt_version="v1",
        )
        db.session.add(inference)
        db.session.commit()

    resp = client.get("/export.csv", headers=auth_header)
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/csv")
    body = resp.get_data(as_text=True)
    assert "エクスポート対象" in body
    assert "82" in body


def test_index_risk_filter(app, client, auth_header):
    with app.app_context():
        high_article = Article(
            url="https://news.yahoo.co.jp/articles/high",
            title="高リスク記事",
            published_at=datetime.now(timezone.utc),
            body="本文",
        )
        low_article = Article(
            url="https://news.yahoo.co.jp/articles/low",
            title="低リスク記事",
            published_at=datetime.now(timezone.utc),
            body="本文",
        )
        db.session.add_all([high_article, low_article])
        db.session.flush()

        db.session.add_all(
            [
                InferenceResult(
                    article_id=high_article.id,
                    risk_score=90,
                    summary="high",
                    model="gpt",
                    prompt_version="v1",
                ),
                InferenceResult(
                    article_id=low_article.id,
                    risk_score=20,
                    summary="low",
                    model="gpt",
                    prompt_version="v1",
                ),
            ]
        )
        db.session.commit()

    resp = client.get("/?risk=high", headers=auth_header)
    text = resp.get_data(as_text=True)
    assert "高リスク記事" in text
    assert "低リスク記事" not in text


def test_index_search_filters_results(app, client, auth_header):
    with app.app_context():
        a1 = Article(
            url="https://news.yahoo.co.jp/articles/filter-1",
            title="AIに関するニュース",
            published_at=None,
            body="本文A",
        )
        a2 = Article(
            url="https://news.yahoo.co.jp/articles/filter-2",
            title="スポーツの話題",
            published_at=None,
            body="本文B",
        )
        db.session.add_all([a1, a2])
        db.session.commit()

    resp = client.get("/?q=AI", headers=auth_header)
    text = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "AIに関するニュース" in text
    assert "スポーツの話題" not in text


def test_index_pagination(app, client, auth_header):
    with app.app_context():
        for i in range(25):
            article = Article(
                url=f"https://news.yahoo.co.jp/articles/page-{i}",
                title=f"記事{i}",
                published_at=None,
                body="本文",
            )
            db.session.add(article)
        db.session.commit()

    resp = client.get("/", headers=auth_header)
    text = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "1 /" in text

    resp_page2 = client.get("/?page=2", headers=auth_header)
    text2 = resp_page2.get_data(as_text=True)
    assert resp_page2.status_code == 200
    assert "2 /" in text2


def test_index_sorting_by_title(app, client, auth_header):
    with app.app_context():
        a = Article(url="https://news.yahoo.co.jp/articles/a", title="あ", published_at=None, body="本文")
        b = Article(url="https://news.yahoo.co.jp/articles/b", title="い", published_at=None, body="本文")
        db.session.add_all([b, a])
        db.session.commit()

    resp = client.get("/?sort=title&order=asc", headers=auth_header)
    text = resp.get_data(as_text=True)
    assert text.index("あ") < text.index("い")


def test_scrape_creates_article(app, client, auth_header, mocker):
    app.config["WTF_CSRF_ENABLED"] = False
    url = "https://news.yahoo.co.jp/articles/example"
    parsed = parsing.ParsedArticle(url=url, title="タイトル", published_at=datetime.utcnow(), body="本文")
    mocker.patch("app.routes.scraping.is_allowed", return_value=True)
    mocker.patch("app.services.articles.scraping.fetch", return_value=mocker.Mock(url=url, text="html"))
    mocker.patch("app.services.articles.parsing.parse_article", return_value=parsed)
    mocker.patch(
        "app.services.articles.ai_service.summarize_and_score",
        return_value=mocker.Mock(summary="要約", risk_score=50, model="gpt", prompt_version="v1"),
    )

    resp = client.post("/scrape", data={"url": url}, headers=auth_header, follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        article = Article.query.filter_by(url=url).first()
        assert article is not None
        assert article.title == "タイトル"


def test_scrape_reuses_existing_article(app, client, auth_header):
    app.config["WTF_CSRF_ENABLED"] = False
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


def test_result_page_not_found_returns_404(client, auth_header):
    resp = client.get("/result/does-not-exist", headers=auth_header)
    assert resp.status_code == 404


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
    assert "推論履歴" not in text


def test_scrape_failure_flash_message(app, client, auth_header, mocker):
    app.config["WTF_CSRF_ENABLED"] = False
    mocker.patch("app.routes.scraping.is_allowed", return_value=True)
    mocker.patch("app.services.articles.scraping.fetch", side_effect=ScrapeError("取得失敗"))

    resp = client.post(
        "/scrape",
        data={"url": "https://news.yahoo.co.jp/articles/error"},
        headers=auth_header,
        follow_redirects=True,
    )

    text = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "取得失敗" in text


def test_rerun_ai_updates_inference(app, client, auth_header, mocker):
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        app.config["ENABLE_AI"] = True
        article = Article(
            url="https://news.yahoo.co.jp/articles/ai-rerun",
            title="AI再実行",
            published_at=None,
            body="本文",
        )
        db.session.add(article)
        db.session.commit()
        article_id = article.id

    mocker.patch(
        "app.services.articles.ai_service.summarize_and_score",
        side_effect=[
            mocker.Mock(
                summary="初回要約",
                risk_score=60,
                model="gpt-test",
                prompt_version="v2",
            ),
            mocker.Mock(
                summary="再実行の要約",
                risk_score=77,
                model="gpt-test",
                prompt_version="v3",
            ),
        ],
    )

    first_resp = client.post(
        f"/result_ai/{article_id}/rerun",
        headers=auth_header,
        follow_redirects=True,
    )
    resp = client.post(
        f"/result_ai/{article_id}/rerun",
        headers=auth_header,
        follow_redirects=True,
    )

    with app.app_context():
        app.config["ENABLE_AI"] = False

    assert first_resp.status_code == 200
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "AI推論を再実行しました" in text
    assert "77" in text
    assert "推論履歴" in text
    assert text.count("gpt-test") >= 2

    with app.app_context():
        refreshed = db.session.get(Article, article_id)
        assert refreshed is not None
        assert len(refreshed.inferences) == 2
        assert refreshed.latest_inference.summary == "再実行の要約"


def test_rerun_ai_respects_disable(app, client, auth_header):
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        article = Article(
            url="https://news.yahoo.co.jp/articles/ai-disabled",
            title="AI無効",
            published_at=None,
            body="本文",
        )
        db.session.add(article)
        db.session.commit()
        article_id = article.id
        app.config["ENABLE_AI"] = False

    resp = client.post(
        f"/result_ai/{article_id}/rerun",
        headers=auth_header,
        follow_redirects=True,
    )

    assert resp.status_code == 200
    assert "AI機能は無効化されています" in resp.get_data(as_text=True)


def test_latest_feed_page_without_search(app, client, auth_header, mocker):
    feed_items = [
        news_feed.NewsFeedItem(
            title=f"記事{i}",
            url=f"https://news.yahoo.co.jp/articles/feed-{i}",
            published_at=datetime.now(timezone.utc),
            source="Yahoo!ニュース",
        )
        for i in range(30)
    ]

    mocker.patch("app.routes.news_feed.fetch_latest_articles", return_value=feed_items)

    resp = client.get("/latest-feed", headers=auth_header)
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "最新のYahoo!ニュースから選ぶ" in text
    assert "記事0" in text
    assert "1 / 2" in text  # Page 1 of 2


def test_latest_feed_page_with_search(app, client, auth_header, mocker):
    feed_items = [
        news_feed.NewsFeedItem(
            title="経済ニュース",
            url="https://news.yahoo.co.jp/articles/economy-1",
            published_at=datetime.now(timezone.utc),
            source="Yahoo!ニュース - 経済",
        ),
        news_feed.NewsFeedItem(
            title="スポーツニュース",
            url="https://news.yahoo.co.jp/articles/sports-1",
            published_at=datetime.now(timezone.utc),
            source="Yahoo!ニュース - スポーツ",
        ),
    ]

    mocker.patch("app.routes.news_feed.fetch_latest_articles", return_value=feed_items)

    resp = client.get("/latest-feed?q=経済", headers=auth_header)
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "経済ニュース" in text
    assert "スポーツニュース" not in text


def test_latest_feed_page_pagination(app, client, auth_header, mocker):
    feed_items = [
        news_feed.NewsFeedItem(
            title=f"記事{i}",
            url=f"https://news.yahoo.co.jp/articles/feed-{i}",
            published_at=datetime.now(timezone.utc),
            source="Yahoo!ニュース",
        )
        for i in range(25)
    ]

    mocker.patch("app.routes.news_feed.fetch_latest_articles", return_value=feed_items)

    resp = client.get("/latest-feed?page=2", headers=auth_header)
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "記事20" in text
    assert "記事24" in text
    assert "2 / 2" in text


# ========================================
# Health Check Tests
# ========================================

def test_health_check_ok(client, monkeypatch):
    """正常なヘルスチェック"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert data["openai_configured"] is True
    assert "timestamp" in data
    assert data["service"] == "scraper-app"


def test_health_check_degraded_no_openai(client, monkeypatch):
    """OpenAI未設定時のヘルスチェック"""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resp = client.get("/health")
    assert resp.status_code == 503
    data = resp.get_json()
    assert data["status"] == "degraded"
    assert data["openai_configured"] is False


def test_readiness_check(client):
    """Readinessチェック"""
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ready"


def test_liveness_check(client):
    """Livenessチェック"""
    resp = client.get("/health/live")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "alive"
