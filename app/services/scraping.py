from __future__ import annotations

import logging
from typing import Any, Final
from urllib.parse import urlparse

import requests
from requests import Response
from requests.adapters import HTTPAdapter, Retry

from flask import current_app, has_app_context

logger = logging.getLogger(__name__)

YAHOO_NEWS_PREFIX: Final[str] = "https://news.yahoo.co.jp/articles/"
ACCIDENT_PREFIX: Final[str] = "https://news.yahoo.co.jp/pickup/"

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
    """仕様で許可されたYahooニュースURLかを判定。"""
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    normalized = url.strip()
    return normalized.startswith(YAHOO_NEWS_PREFIX) or normalized.startswith(ACCIDENT_PREFIX)


def _build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=_config_get("SCRAPE_RETRY_TOTAL", DEFAULT_RETRY_TOTAL),
        backoff_factor=_config_get("SCRAPE_RETRY_BACKOFF", DEFAULT_RETRY_BACKOFF),
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": _config_get("USER_AGENT", DEFAULT_USER_AGENT)})
    return session


def fetch(url: str) -> Response:
    if not is_allowed(url):
        raise ScrapeError("許可されたYahoo!ニュースのURLではありません。")

    session = _build_session()
    timeout = _config_get("REQUEST_TIMEOUT", DEFAULT_REQUEST_TIMEOUT)
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        # 文字化け対策
        if response.encoding is None:
            response.encoding = response.apparent_encoding
        return response
    except requests.RequestException as exc:  # pragma: no cover - 通信周りはモック化
        logger.exception("Failed to fetch article: %s", exc)
        raise ScrapeError("記事の取得に失敗しました。") from exc
