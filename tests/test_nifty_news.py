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
    assert is_nifty_news_url("https://news.nifty.com/article/domestic/government/12145-4674454/")
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
            "datePublished": "2025-11-11T12:00:00+09:00",
            "description": "テスト記事の説明文です"
        }
        </script>
    </head>
    <body>
        <div class="article_body_text">
            <div id="article_body_text_sentence">
                <p>これはテスト記事の本文です。十分な長さのテキストです。</p>
                <p>複数の段落があります。こちらも十分な長さです。</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    result = NiftyNewsParser.parse_article(html, "https://news.nifty.com/article/test/123/")
    
    assert result.title == "テスト記事タイトル"
    assert result.published_at is not None
    assert "テスト記事の本文" in result.body
    assert "複数の段落" in result.body


def test_parse_nifty_article_fallback():
    """JSON-LDなしの@niftyニュース記事のパーステスト（フォールバック）"""
    html = """
    <html>
    <head>
        <meta property="og:title" content="フォールバックタイトル｜ニフティニュース">
    </head>
    <body>
        <article class="article">
            <p>これはフォールバックテストです。十分な長さがあるテキストです。</p>
            <p>本文が正しく取得されるはずです。こちらも十分な長さです。</p>
        </article>
    </body>
    </html>
    """
    
    result = NiftyNewsParser.parse_article(html, "https://news.nifty.com/article/test/456/")
    
    assert result.title == "フォールバックタイトル"
    # JSON-LDなしの場合、日時はNoneになる可能性がある
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
