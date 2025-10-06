"""AIリスクスコアからラベルやしきい値を導出するユーティリティ。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RiskBand:
    slug: str
    name: str
    badge: str
    description: str
    min_score: int
    max_score: int | None


_LEVELS: tuple[RiskBand, ...] = (
    RiskBand(
        slug="high",
        name="High",
        badge="要警戒",
        description="重大インシデントが想定される高リスク",
        min_score=80,
        max_score=None,
    ),
    RiskBand(
        slug="elevated",
        name="Elevated",
        badge="注意",
        description="被害拡大の恐れがあるリスク",
        min_score=60,
        max_score=79,
    ),
    RiskBand(
        slug="moderate",
        name="Moderate",
        badge="観測",
        description="状況把握が必要な中程度リスク",
        min_score=40,
        max_score=59,
    ),
    RiskBand(
        slug="low",
        name="Low",
        badge="低リスク",
        description="深刻な影響は想定されにくい",
        min_score=0,
        max_score=39,
    ),
)


def classify(score: int | None) -> RiskBand | None:
    if score is None:
        return None
    for band in _LEVELS:
        if band.max_score is None and score >= band.min_score:
            return band
        if band.max_score is not None and band.min_score <= score <= band.max_score:
            return band
    return _LEVELS[-1]


def levels() -> tuple[RiskBand, ...]:
    return _LEVELS


def level_by_slug(slug: str | None) -> RiskBand | None:
    if not slug:
        return None
    slug = slug.lower()
    for band in _LEVELS:
        if band.slug == slug:
            return band
    return None


def slugs() -> Iterable[str]:
    return (band.slug for band in _LEVELS)
