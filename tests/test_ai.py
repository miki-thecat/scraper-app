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
    class FakeCompletions:
        def create(self, **kwargs):
            message = SimpleNamespace(content='{"summary": "要約", "risk_score": 42}')
            choice = SimpleNamespace(message=message)
            return SimpleNamespace(choices=[choice])

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = FakeChat()

    with app.app_context():
        app.config["ENABLE_AI"] = True
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        monkeypatch.setattr(ai_service, "OpenAI", FakeOpenAI)
        result = ai_service.summarize_and_score("title", "body")
        assert result.summary == "要約"
        assert result.risk_score == 42
        assert result.model == app.config["OPENAI_MODEL"]
