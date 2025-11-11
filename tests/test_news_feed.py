from __future__ import annotations

from datetime import timezone

from app.services import news_feed


SAMPLE_FEED = """
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Yahoo!ニュース - トピックス</title>
    <item>
      <title>記事A</title>
      <link>https://news.yahoo.co.jp/articles/article-a</link>
      <pubDate>Tue, 08 Oct 2024 12:00:00 +0900</pubDate>
    </item>
    <item>
      <title>記事B</title>
      <link>https://news.yahoo.co.jp/articles/article-b</link>
      <pubDate>Tue, 08 Oct 2024 09:30:00 +0900</pubDate>
    </item>
  </channel>
</rss>
""".strip()


SAMPLE_FEED_DUP = """
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Yahoo!ニュース - トピックス2</title>
    <item>
      <title>記事B別視点</title>
      <link>https://news.yahoo.co.jp/articles/article-b</link>
      <pubDate>Tue, 08 Oct 2024 09:45:00 +0900</pubDate>
    </item>
    <item>
      <title>記事C</title>
      <link>https://news.yahoo.co.jp/articles/article-c</link>
      <pubDate>Tue, 08 Oct 2024 08:15:00 +0900</pubDate>
    </item>
  </channel>
</rss>
""".strip()


def _mock_response(text, mocker):
    response = mocker.Mock()
    response.text = text
    response.raise_for_status = mocker.Mock()
    return response


def test_fetch_latest_articles_merges_and_sorts(app, mocker):
    with app.app_context():
        news_feed.clear_cache()
        app.config["NEWS_FEED_URLS"] = (
            "https://example.com/feed1.xml",
            "https://example.com/feed2.xml",
        )

        responses = {
            "https://example.com/feed1.xml": _mock_response(SAMPLE_FEED, mocker),
            "https://example.com/feed2.xml": _mock_response(SAMPLE_FEED_DUP, mocker),
        }

        def fake_get(url, timeout):
            return responses[url]

        mocker.patch("app.services.news_feed.requests.get", side_effect=fake_get)

        items = news_feed.fetch_latest_articles(limit=5, provider="yahoo")

        assert [item.title for item in items] == ["記事A", "記事B別視点", "記事C"]
        assert items[0].published_at.tzinfo == timezone.utc
        assert all(item.provider == "yahoo" for item in items)


def test_fetch_latest_articles_uses_cache(app, mocker):
    with app.app_context():
        news_feed.clear_cache()
        app.config["NEWS_FEED_URLS"] = ("https://example.com/feed1.xml",)

        mock_get = mocker.patch(
            "app.services.news_feed.requests.get",
            return_value=_mock_response(SAMPLE_FEED, mocker),
        )

        first = news_feed.fetch_latest_articles(limit=2, provider="yahoo")
        second = news_feed.fetch_latest_articles(limit=2, provider="yahoo")

        assert mock_get.call_count == 1
        assert first[0].title == second[0].title


def test_fetch_latest_articles_supports_multiple_providers(app, mocker):
    with app.app_context():
        news_feed.clear_cache()
        app.config["ENABLED_FEED_PROVIDERS"] = ("nifty",)
        app.config["NIFTY_FEED_URLS"] = ("https://example.com/nifty.xml",)
        mocker.patch(
            "app.services.news_feed.requests.get",
            return_value=_mock_response(SAMPLE_FEED, mocker),
        )
        items = news_feed.fetch_latest_articles(limit=1, provider="nifty")
        assert items[0].provider == "nifty"


def test_enabled_providers_defaults(app):
    with app.app_context():
        providers = news_feed.enabled_providers()
        assert providers[0] == "yahoo"
