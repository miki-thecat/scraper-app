from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from app.services import ai as ai_service


def test_ai_service_disabled(app):
    with app.app_context():
        app.config["ENABLE_AI"] = False
        with pytest.raises(ai_service.AIServiceUnavailable):
            ai_service.summarize_and_score("title", "body")


def test_ai_requires_api_key(app, monkeypatch):
    with app.app_context():
        app.config["ENABLE_AI"] = True
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ai_service.AIServiceUnavailable):
            ai_service.summarize_and_score("title", "body")


def test_ai_parses_response(app, monkeypatch):
    class FakeResponses:
        def create(self, **kwargs):
            text = SimpleNamespace(value='{"summary": "要約", "risk_score": 42}')
            content = SimpleNamespace(text=text)
            output = SimpleNamespace(content=[content])
            return SimpleNamespace(output=[output])

    class FakeOpenAI:
        def __init__(self, *args, **kwargs):
            self.responses = FakeResponses()

    with app.app_context():
        app.config["ENABLE_AI"] = True
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        monkeypatch.setattr(ai_service, "OpenAI", FakeOpenAI)
        result = ai_service.summarize_and_score("title", "body")
        assert result.summary == "要約"
        assert result.risk_score == 42
        assert result.model == app.config["OPENAI_MODEL"]
