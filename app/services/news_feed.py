"""Yahoo!/ニフティのRSSから最新記事を取得するユーティリティ。"""
from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Sequence

import requests
from dateutil import parser as dateparser
from flask import current_app

logger = logging.getLogger(__name__)


from app.blueprints.virtual_news import ARTICLES

_DEFAULT_PROVIDERS: tuple[str, ...] = ("virtual_news",)

_PROVIDER_SETTINGS = {
    "virtual_news": {
        "config_key": "VIRTUAL_NEWS_FEED_URLS",
        "label": "Virtual News",
        "defaults": (
            "http://localhost:5000/virtual-news/",
        ),
    },
}


@dataclass(slots=True)
class NewsFeedItem:
    """最新記事のメタデータ。"""

    title: str
    url: str
    published_at: datetime | None
    source: str
    provider: str


class NewsFeedError(RuntimeError):
    """RSS取得・解析時の例外。"""


_CACHE: dict[str, tuple[float, List[NewsFeedItem]]] = {}
_CACHE_TTL = 300.0  # 5 minutes


def clear_cache() -> None:
    """テスト向け。モジュール内キャッシュを破棄する。"""

    _CACHE.clear()


def provider_label(provider: str) -> str:
    settings = _PROVIDER_SETTINGS.get(provider.lower())
    if not settings:
        return provider.title()
    return settings["label"]


def enabled_providers() -> tuple[str, ...]:
    configured: Sequence[str] = current_app.config.get("ENABLED_FEED_PROVIDERS") or _DEFAULT_PROVIDERS
    filtered = tuple(p for p in (slug.lower() for slug in configured) if p in _PROVIDER_SETTINGS)
    return filtered or ("virtual_news",)


def _feed_urls(provider: str) -> Iterable[str]:
    provider = provider.lower()
    settings = _PROVIDER_SETTINGS.get(provider)
    if not settings:
        return ()
    config_value = current_app.config.get(settings["config_key"])
    if config_value:
        urls = config_value
    else:
        urls = settings.get("defaults", ())
    for url in urls:
        if url:
            yield url


def _request_timeout() -> int:
    return int(current_app.config.get("NEWS_FEED_TIMEOUT", 5))


def fetch_latest_articles(limit: int = 6, provider: str = "virtual_news") -> list[NewsFeedItem]:
    """指定したニュースプロバイダのRSSから最新記事をまとめて返す（モック版）。"""

    # Virtual Newsのデータを直接使用
    items = []

    # 辞書をリストに変換してソート
    articles_list = [{"id": k, **v} for k, v in ARTICLES.items()]
    articles_list.sort(key=lambda x: x['published_at'], reverse=True)

    provider_name = provider_label(provider)

    for article in articles_list[:limit]:
        # published_atはISO文字列なのでdatetimeに変換
        try:
            published_at = datetime.fromisoformat(article['published_at'])
            # タイムゾーン情報がない場合はUTCとする（簡易的）
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
        except ValueError:
            published_at = datetime.now(timezone.utc)

        items.append(
            NewsFeedItem(
                title=article['title'],
                url=f"http://localhost:5000/virtual-news/article/{article['id']}",
                published_at=published_at,
                source=provider_name,
                provider=provider,
            )
        )

    return items
