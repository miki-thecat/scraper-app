"""Yahoo!ニュースのRSSから最新記事を取得するユーティリティ。"""
from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List

import requests
from dateutil import parser as dateparser
from flask import current_app

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NewsFeedItem:
    """最新記事のメタデータ。"""

    title: str
    url: str
    published_at: datetime | None
    source: str


class NewsFeedError(RuntimeError):
    """RSS取得・解析時の例外。"""


_CACHE: dict[str, tuple[float, List[NewsFeedItem]]] = {}
_CACHE_TTL = 300.0  # 5 minutes


def clear_cache() -> None:
    """テスト向け。モジュール内キャッシュを破棄する。"""

    _CACHE.clear()


def _feed_urls() -> Iterable[str]:
    cfg_urls = current_app.config.get(
        "NEWS_FEED_URLS",
        (
            # 主要カテゴリ（9種類 × 8件 = 72件）
            "https://news.yahoo.co.jp/rss/topics/top-picks.xml",
            "https://news.yahoo.co.jp/rss/topics/domestic.xml",
            "https://news.yahoo.co.jp/rss/topics/world.xml",
            "https://news.yahoo.co.jp/rss/topics/business.xml",
            "https://news.yahoo.co.jp/rss/topics/entertainment.xml",
            "https://news.yahoo.co.jp/rss/topics/sports.xml",
            "https://news.yahoo.co.jp/rss/topics/it.xml",
            "https://news.yahoo.co.jp/rss/topics/science.xml",
            "https://news.yahoo.co.jp/rss/topics/local.xml",
            # メディア別フィード（約590件）
            "https://news.yahoo.co.jp/rss/media/jprime/all.xml",
            "https://news.yahoo.co.jp/rss/media/nksports/all.xml",
            "https://news.yahoo.co.jp/rss/media/natalien/all.xml",
            "https://news.yahoo.co.jp/rss/media/natalieo/all.xml",
            "https://news.yahoo.co.jp/rss/media/tospoweb/all.xml",
            "https://news.yahoo.co.jp/rss/media/baseballk/all.xml",
            "https://news.yahoo.co.jp/rss/media/soccerk/all.xml",
            "https://news.yahoo.co.jp/rss/media/bfj/all.xml",
            "https://news.yahoo.co.jp/rss/media/bengocom/all.xml",
            "https://news.yahoo.co.jp/rss/media/zdn_mkt/all.xml",
            "https://news.yahoo.co.jp/rss/media/bcn/all.xml",
            "https://news.yahoo.co.jp/rss/media/impress/all.xml",
        ),
    )
    for url in cfg_urls:
        if url:
            yield url


def _request_timeout() -> int:
    return int(current_app.config.get("NEWS_FEED_TIMEOUT", 5))


def fetch_latest_articles(limit: int = 6) -> list[NewsFeedItem]:
    """Yahoo!ニュースのRSSから最新記事をまとめて返す。

    キャッシュ（5分）を利用して無駄なリクエストを避ける。
    取得できなかった場合は空リストを返す。
    """

    cache_key = f"default:{limit}"
    cached = _CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1][:limit]

    articles: dict[str, NewsFeedItem] = {}

    for url in _feed_urls():
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
        channel_title = (channel.findtext("title") if channel is not None else "Yahoo!ニュース").strip()

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
                source=channel_title or "Yahoo!ニュース",
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
