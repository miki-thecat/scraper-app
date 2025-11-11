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

_DEFAULT_PROVIDERS: tuple[str, ...] = ("yahoo", "nifty")

_PROVIDER_SETTINGS = {
    "yahoo": {
        "config_key": "NEWS_FEED_URLS",
        "label": "Yahoo!ニュース",
        "defaults": (
            "https://news.yahoo.co.jp/rss/topics/top-picks.xml",
            "https://news.yahoo.co.jp/rss/topics/domestic.xml",
            "https://news.yahoo.co.jp/rss/topics/world.xml",
            "https://news.yahoo.co.jp/rss/topics/business.xml",
            "https://news.yahoo.co.jp/rss/topics/entertainment.xml",
            "https://news.yahoo.co.jp/rss/topics/sports.xml",
            "https://news.yahoo.co.jp/rss/topics/it.xml",
            "https://news.yahoo.co.jp/rss/topics/science.xml",
            "https://news.yahoo.co.jp/rss/topics/local.xml",
        ),
    },
    "nifty": {
        "config_key": "NIFTY_FEED_URLS",
        "label": "ニフティニュース",
        "defaults": (
            "https://news.nifty.com/rss/topics_pickup.xml",
            "https://news.nifty.com/rss/topics_domestic.xml",
            "https://news.nifty.com/rss/topics_world.xml",
            "https://news.nifty.com/rss/topics_economy.xml",
            "https://news.nifty.com/rss/topics_entame.xml",
            "https://news.nifty.com/rss/topics_sports.xml",
            "https://news.nifty.com/rss/topics_technology.xml",
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
    return filtered or ("yahoo",)


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


def fetch_latest_articles(limit: int = 6, provider: str = "yahoo") -> list[NewsFeedItem]:
    """指定したニュースプロバイダのRSSから最新記事をまとめて返す。"""

    provider = provider.lower()
    if provider not in _PROVIDER_SETTINGS:
        raise NewsFeedError(f"Unknown provider: {provider}")

    cache_key = f"{provider}:{limit}"
    cached = _CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1][:limit]

    articles: dict[str, NewsFeedItem] = {}

    for url in _feed_urls(provider):
        try:
            response = requests.get(url, timeout=_request_timeout())
            response.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover - ネットワーク失敗はログのみ
            logger.warning("Failed to fetch RSS feed %s: %s", url, exc)
            continue

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            logger.warning("Failed to parse RSS feed %s: %s", url, exc)
            continue

        channel = root.find("channel")
        channel_title = (channel.findtext("title") if channel is not None else provider_label(provider)).strip()

        if channel is None:
            logger.debug("RSS feed %s had no channel element", url)
            continue

        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()

            if not title or not link:
                continue

            pub_date_raw = (item.findtext("pubDate") or "").strip()
            try:
                published_at = dateparser.parse(pub_date_raw) if pub_date_raw else None
            except (ValueError, TypeError, OverflowError):
                published_at = None
            else:
                if published_at and published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)

                if published_at:
                    try:
                        published_at = published_at.astimezone(timezone.utc)
                    except ValueError:
                        published_at = None

            article = NewsFeedItem(
                title=title,
                url=link,
                published_at=published_at,
                source=channel_title or provider_label(provider),
                provider=provider,
            )
            # 同じURLは最新のものを優先
            articles[link] = article

    def _sort_key(item: NewsFeedItem) -> float:
        if item.published_at:
            try:
                return item.published_at.timestamp()
            except OSError:  # pragma: no cover - 古い日時のtimestamp化失敗
                return float("-inf")
        return float("-inf")

    latest_articles = sorted(articles.values(), key=_sort_key, reverse=True)

    sliced = latest_articles[:limit] if limit <= len(latest_articles) else latest_articles
    _CACHE[cache_key] = (now, sliced)
    return sliced
