from __future__ import annotations

from datetime import datetime

from app.services import parsing


SAMPLE_HTML = """
<!doctype html>
<html>
<head>
    <title>サンプル記事</title>
    <meta property="og:title" content="OGPタイトル">
    <script type="application/ld+json">
    {
        "@context": "http://schema.org",
        "@type": "NewsArticle",
        "headline": "JSON-LDタイトル",
        "datePublished": "2024-05-01T10:30:00+09:00",
        "articleBody": "段落1\n段落2"
    }
    </script>
</head>
<body>
    <article>
        <p>段落1</p>
        <p>段落2</p>
    </article>
</body>
</html>
"""


def test_parse_article_prefers_json_ld():
    parsed = parsing.parse_article("https://news.yahoo.co.jp/articles/example", SAMPLE_HTML)
    assert parsed.title == "JSON-LDタイトル"
    assert parsed.body == "段落1\n段落2"
    assert isinstance(parsed.published_at, datetime)


def test_parse_article_fallback_when_json_ld_missing():
    html = SAMPLE_HTML.replace("application/ld+json", "application/json")
    parsed = parsing.parse_article("https://news.yahoo.co.jp/articles/example", html)
    assert parsed.title == "OGPタイトル"
    assert "段落" in parsed.body
