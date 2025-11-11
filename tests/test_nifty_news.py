"""
@niftyニュース統合のテスト
"""
from __future__ import annotations

import pytest

from app.services.nifty_news import NiftyNewsParser, is_nifty_news_url


def test_is_nifty_news_url():
    """@niftyニュースのURL判定テスト"""
    assert is_nifty_news_url("https://news.nifty.com/topics/domestic/240101000001/")
    assert is_nifty_news_url("https://news.nifty.com/topics/world/test123/")
    assert not is_nifty_news_url("https://news.yahoo.co.jp/articles/abc123")
    assert not is_nifty_news_url("https://example.com/article")


def test_parse_nifty_article_with_json_ld():
    """JSON-LDを含む@niftyニュース記事のパーステスト"""
    html = """
    <html>
    <head>
        <meta property="og:title" content="テスト記事タイトル">
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": "テスト記事タイトル",
            "datePublished": "2025-11-11T12:00:00+09:00"
        }
        </script>
    </head>
    <body>
        <div class="article_body">
            <p>これはテスト記事の本文です。</p>
            <p>複数の段落があります。</p>
        </div>
    </body>
    </html>
    """
    
    result = NiftyNewsParser.parse_article(html, "https://news.nifty.com/topics/test/123/")
    
    assert result.title == "テスト記事タイトル"
    assert result.published_at is not None
    assert "テスト記事の本文" in result.body
    assert "複数の段落" in result.body


def test_parse_nifty_article_fallback():
    """JSON-LDなしの@niftyニュース記事のパーステスト（フォールバック）"""
    html = """
    <html>
    <head>
        <meta property="og:title" content="フォールバックタイトル">
    </head>
    <body>
        <time class="article_date" datetime="2025-11-11T15:00:00+09:00"></time>
        <article>
            <p>これはフォールバックテストです。</p>
            <p>本文が正しく取得されるはずです。</p>
        </article>
    </body>
    </html>
    """
    
    result = NiftyNewsParser.parse_article(html, "https://news.nifty.com/topics/test/456/")
    
    assert result.title == "フォールバックタイトル"
    assert result.published_at is not None
    assert "フォールバックテスト" in result.body


def test_parse_nifty_article_minimal():
    """最小限の情報しかない記事のパーステスト"""
    html = """
    <html>
    <body>
        <h1>最小限タイトル</h1>
        <p>短い</p>
    </body>
    </html>
    """
    
    result = NiftyNewsParser.parse_article(html, "https://news.nifty.com/topics/test/789/")
    
    assert result.title == "最小限タイトル"
    # 短すぎる本文は除外されるため、フォールバックメッセージが返る
    assert result.body == "本文取得失敗"
