from __future__ import annotations

from types import SimpleNamespace

from app.services import scraping


def test_is_allowed_accepts_valid_prefix():
    assert scraping.is_allowed("https://news.yahoo.co.jp/articles/abc123")
    assert scraping.is_allowed("https://news.yahoo.co.jp/pickup/abc123")
    assert scraping.is_allowed("https://news.nifty.com/article/domestic/gov/12345/")


def test_is_allowed_rejects_invalid():
    assert not scraping.is_allowed("https://example.com/news")
    assert not scraping.is_allowed("javascript:alert(1)")


def test_fetch_success(app, mocker):
    class FakeResponse:
        url = "https://news.yahoo.co.jp/articles/example"
        text = "<html></html>"
        status_code = 200
        encoding = None

        def raise_for_status(self):
            return None

        apparent_encoding = "utf-8"

    class FakeSession(SimpleNamespace):
        def get(self, url, timeout):
            return FakeResponse()

    mocker.patch.object(scraping, "_build_session", return_value=FakeSession())
    response = scraping.fetch("https://news.yahoo.co.jp/articles/example")
    assert response.text == "<html></html>"
    assert response.url.endswith("/example")
