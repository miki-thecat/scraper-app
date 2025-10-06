from __future__ import annotations

from app.services import risk


def test_risk_classification_levels():
    high = risk.classify(85)
    assert high is not None
    assert high.slug == "high"
    assert high.badge == "要警戒"

    elevated = risk.classify(72)
    assert elevated is not None
    assert elevated.slug == "elevated"

    low = risk.classify(30)
    assert low is not None
    assert low.slug == "low"

    assert risk.classify(None) is None


def test_risk_levels_and_lookup():
    levels = risk.levels()
    assert {band.slug for band in levels} == {"high", "elevated", "moderate", "low"}
    assert risk.level_by_slug("moderate").min_score == 40
    assert risk.level_by_slug("unknown") is None
