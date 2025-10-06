from __future__ import annotations

import os
from datetime import timedelta


class Config:
    """アプリケーション全体の基礎設定。"""

    SECRET_KEY = os.getenv("SECRET_KEY", "change_me_secret")

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", os.getenv("DATABASE_URI", "sqlite:///local.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Basic Auth
    BASIC_AUTH_USERNAME = os.getenv("BASIC_AUTH_USERNAME", "admin")
    BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "password")
    API_ACCESS_TOKENS = tuple(
        token.strip()
        for token in os.getenv("API_ACCESS_TOKENS", "").split(",")
        if token.strip()
    )

    # Request / scraping constraints
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))
    SCRAPE_RETRY_TOTAL = int(os.getenv("SCRAPE_RETRY_TOTAL", "2"))
    SCRAPE_RETRY_BACKOFF = float(os.getenv("SCRAPE_RETRY_BACKOFF", "0.5"))
    USER_AGENT = os.getenv(
        "SCRAPER_USER_AGENT",
        "Mozilla/5.0 (compatible; ScraperApp/1.0; +https://example.com/bot)",
    )
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Feed settings
    NEWS_FEED_URLS = tuple(
        token.strip()
        for token in os.getenv(
            "NEWS_FEED_URLS",
            "https://news.yahoo.co.jp/rss/topics/top-picks.xml,https://news.yahoo.co.jp/rss/topics/domestic.xml",
        ).split(",")
        if token.strip()
    )
    NEWS_FEED_TIMEOUT = int(os.getenv("NEWS_FEED_TIMEOUT", "5"))

    # OpenAI / AI settings
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "30"))
    PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1")
    ENABLE_AI = os.getenv("ENABLE_AI", "1") not in {"0", "false", "False"}

    # Misc
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)


class TestConfig(Config):
    """pytest向けの設定。"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    BASIC_AUTH_USERNAME = "test"
    BASIC_AUTH_PASSWORD = "test"
    ENABLE_AI = False
    API_ACCESS_TOKENS = ("test-token",)
    RATE_LIMIT_PER_MINUTE = 1000
    NEWS_FEED_URLS: tuple[str, ...] = ()


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False
