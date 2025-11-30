from __future__ import annotations

import logging
from typing import Any, Final
from urllib.parse import urlparse

import requests
from requests import HTTPError, Response
from requests.adapters import HTTPAdapter, Retry

from flask import current_app, has_app_context

logger = logging.getLogger(__name__)

YAHOO_NEWS_PREFIX: Final[str] = "https://news.yahoo.co.jp/articles/"
ACCIDENT_PREFIX: Final[str] = "https://news.yahoo.co.jp/pickup/"
NIFTY_NEWS_PREFIX: Final[str] = "https://news.nifty.com/"

DEFAULT_USER_AGENT: Final[str] = "Mozilla/5.0 (compatible; ScraperApp/1.0; +https://example.com/bot)"
DEFAULT_REQUEST_TIMEOUT: Final[int] = 10
DEFAULT_RETRY_TOTAL: Final[int] = 2
DEFAULT_RETRY_BACKOFF: Final[float] = 0.5


def _config_get(key: str, default: Any) -> Any:
    if has_app_context():
        return current_app.config.get(key, default)
    return default


class ScrapeError(RuntimeError):
    """スクレイピング全般のエラー。"""


def is_allowed(url: str) -> bool:
    """仕様で許可されたニュースURLかを判定。"""
    # Virtual Newsは許可
    if "virtual-news" in url:
        return True
    # その他は一旦許可（要件に合わせて調整）
    return True


def fetch(url: str) -> Response:
    """指定されたURLの記事を取得する。"""

    # Virtual Newsの場合は実際にリクエストを送る（localhostへ）
    if "virtual-news" in url:
        # URLが相対パスや不完全な場合は補完が必要だが、
        # ここでは完全なURLが渡されると仮定、もしくはlocalhostを付与
        if url.startswith("/"):
            url = f"http://localhost:5000{url}"

        try:
            return requests.get(url, timeout=DEFAULT_REQUEST_TIMEOUT)
        except requests.RequestException as e:
            raise ScrapeError(f"Failed to fetch {url}: {e}")

    # 既存のモックロジック（Yahoo/Nifty用だが、今回はVirtual News以外は使わない想定）
    # ...

    # モックレスポンス生成
    response = Response()
    response.status_code = 200
    response.encoding = "utf-8"

    # ダミーのHTMLコンテンツ
    dummy_html = f"""
    <html>
        <head><title>モック記事</title></head>
        <body>
            <h1>これはモック記事です</h1>
            <p>著作権の問題を回避するため、実際の内容は表示されません。</p>
            <p>元のURL: {url}</p>
            <div class="article-body">
                <p>ここに記事の本文が入ります。これはダミーテキストです。</p>
                <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
            </div>
        </body>
    </html>
    """

    # requestsの内部APIを使ってコンテンツを設定
    response._content = dummy_html.encode("utf-8")
    response.url = url # URLを設定

    return response
