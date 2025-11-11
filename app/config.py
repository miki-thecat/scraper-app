from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_database_uri(value: str) -> str:
    if not value.startswith("sqlite:///"):
        return value
    path = value.replace("sqlite:///", "", 1)
    if os.path.isabs(path):
        return value
    abs_path = BASE_DIR.joinpath(path).resolve()
    return f"sqlite:///{abs_path}"


class Config:
    """アプリケーション全体の基礎設定。"""

    SECRET_KEY = os.getenv("SECRET_KEY", "change_me_secret")

    # Database
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri(
        os.getenv("DATABASE_URL", os.getenv("DATABASE_URI", "sqlite:///local.db"))
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
    
    # News sources
    YAHOO_NEWS_URL_PREFIX = "https://news.yahoo.co.jp/articles/"
    NIFTY_NEWS_URL_PREFIX = "https://news.nifty.com/topics/"

    # Feed settings
    NEWS_FEED_URLS = tuple(
        token.strip()
        for token in os.getenv(
            "NEWS_FEED_URLS",
            # 主要カテゴリ（9種類 × 8件 = 72件）
            "https://news.yahoo.co.jp/rss/topics/top-picks.xml,"
            "https://news.yahoo.co.jp/rss/topics/domestic.xml,"
            "https://news.yahoo.co.jp/rss/topics/world.xml,"
            "https://news.yahoo.co.jp/rss/topics/business.xml,"
            "https://news.yahoo.co.jp/rss/topics/entertainment.xml,"
            "https://news.yahoo.co.jp/rss/topics/sports.xml,"
            "https://news.yahoo.co.jp/rss/topics/it.xml,"
            "https://news.yahoo.co.jp/rss/topics/science.xml,"
            "https://news.yahoo.co.jp/rss/topics/local.xml,"
            # メディア別フィード（約590件）
            "https://news.yahoo.co.jp/rss/media/jprime/all.xml,"
            "https://news.yahoo.co.jp/rss/media/nksports/all.xml,"
            "https://news.yahoo.co.jp/rss/media/natalien/all.xml,"
            "https://news.yahoo.co.jp/rss/media/natalieo/all.xml,"
            "https://news.yahoo.co.jp/rss/media/tospoweb/all.xml,"
            "https://news.yahoo.co.jp/rss/media/baseballk/all.xml,"
            "https://news.yahoo.co.jp/rss/media/soccerk/all.xml,"
            "https://news.yahoo.co.jp/rss/media/bfj/all.xml,"
            "https://news.yahoo.co.jp/rss/media/bengocom/all.xml,"
            "https://news.yahoo.co.jp/rss/media/zdn_mkt/all.xml,"
            "https://news.yahoo.co.jp/rss/media/bcn/all.xml,"
            "https://news.yahoo.co.jp/rss/media/impress/all.xml",
        ).split(",")
        if token.strip()
    )
    NEWS_FEED_TIMEOUT = int(os.getenv("NEWS_FEED_TIMEOUT", "5"))
    NIFTY_FEED_URLS = tuple(
        token.strip()
        for token in os.getenv(
            "NIFTY_FEED_URLS",
            "https://news.nifty.com/rss/domestic.xml,"
            "https://news.nifty.com/rss/world.xml,"
            "https://news.nifty.com/rss/economy.xml,"
            "https://news.nifty.com/rss/entertainment.xml,"
            "https://news.nifty.com/rss/it.xml,"
            "https://news.nifty.com/rss/sports.xml,"
            "https://news.nifty.com/rss/social.xml,"
            "https://news.nifty.com/rss/science.xml",
        ).split(",")
        if token.strip()
    )
    ENABLED_FEED_PROVIDERS = tuple(
        slug.strip().lower()
        for slug in os.getenv("ENABLED_FEED_PROVIDERS", "yahoo,nifty").split(",")
        if slug.strip()
    )

    # OpenAI / AI settings
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "30"))
    PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1")
    ENABLE_AI = os.getenv("ENABLE_AI", "1") not in {"0", "false", "False"}

    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SSL_STRICT = False
    WTF_CSRF_CHECK_DEFAULT = True

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
    WTF_CSRF_SSL_STRICT = True
