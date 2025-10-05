from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup
from dateutil import parser as dateparser


@dataclass(slots=True)
class ParsedArticle:
    url: str
    title: str
    published_at: datetime | None
    body: str


class ParseError(RuntimeError):
    pass


JSON_LD_TYPES = {"NewsArticle", "Article"}


def parse_article(url: str, html: str) -> ParsedArticle:
    soup = BeautifulSoup(html, "lxml")

    data = _parse_from_json_ld(soup)
    if data:
        title = data.get("title") or data.get("headline") or _fallback_title(soup)
        published = _parse_datetime(data.get("datePublished"))
        body = data.get("articleBody") or _extract_body_from_dom(soup)
        return ParsedArticle(url=url, title=title, published_at=published, body=body)

    title = _fallback_title(soup)
    published = _parse_datetime(_find_meta_content(soup))
    body = _extract_body_from_dom(soup)

    if not body:
        raise ParseError("本文を抽出できませんでした。")

    return ParsedArticle(url=url, title=title, published_at=published, body=body)


def _parse_from_json_ld(soup: BeautifulSoup) -> dict[str, Any] | None:
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        raw_json = script.string or ""
        if not raw_json.strip():
            continue
        try:
            data = json.loads(raw_json, strict=False)
        except json.JSONDecodeError:
            continue

        if isinstance(data, list):
            candidates = data
        else:
            candidates = [data]

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            if candidate.get("@type") in JSON_LD_TYPES:
                return candidate
    return None


def _fallback_title(soup: BeautifulSoup) -> str:
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    heading = soup.find("h1")
    if heading:
        return heading.get_text(strip=True)
    return "(タイトル不明)"


def _find_meta_content(soup: BeautifulSoup) -> str | None:
    for attr in ("datePublished", "article:published_time", "pubdate"):
        meta = soup.find("meta", attrs={"property": attr}) or soup.find("meta", attrs={"name": attr})
        if meta and meta.get("content"):
            return meta["content"].strip()
    time_tag = soup.find("time")
    if time_tag:
        return (time_tag.get("datetime") or time_tag.get_text(strip=True) or None)
    return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = dateparser.parse(value)
    except (ValueError, TypeError, OverflowError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        from dateutil import tz

        dt = dt.replace(tzinfo=tz.gettz("Asia/Tokyo"))
    return dt


def _extract_body_from_dom(soup: BeautifulSoup) -> str:
    selectors = [
        "article p",
        "div.article_body p",
        "div.article_body__item",
        "div#uamods-pickup p",
    ]
    paragraphs: list[str] = []
    for selector in selectors:
        nodes = soup.select(selector)
        candidate = [node.get_text(strip=True) for node in nodes if node.get_text(strip=True)]
        if candidate:
            paragraphs = candidate
            break
    return "\n\n".join(paragraphs)
