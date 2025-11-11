"""
@niftyニュース専用のスクレイピング/パース処理
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from .parsing import ParsedArticle


class NiftyNewsParser:
    """@niftyニュース記事の解析"""

    BASE_URL = "https://news.nifty.com"

    @staticmethod
    def is_nifty_news_url(url: str) -> bool:
        """@niftyニュースのURLか判定"""
        return url.startswith("https://news.nifty.com/topics/")

    @staticmethod
    def parse_article(html: str, url: str) -> ParsedArticle:
        """
        @niftyニュース記事をパース
        
        Args:
            html: HTML文字列
            url: 記事URL
            
        Returns:
            ParsedArticle: パース結果
        """
        soup = BeautifulSoup(html, 'lxml')

        # タイトル取得
        title = None
        # 複数のセレクタを試す
        for selector in ['h1.article_title', 'h1', 'meta[property="og:title"]']:
            if 'meta' in selector:
                meta_tag = soup.find('meta', property='og:title')
                if meta_tag and meta_tag.get('content'):
                    title = meta_tag['content']
                    break
            else:
                title_tag = soup.select_one(selector)
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    break

        # 公開日時取得
        published_at = None
        # JSON-LDから取得
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and 'datePublished' in data:
                    published_at = datetime.fromisoformat(
                        data['datePublished'].replace('Z', '+00:00')
                    )
                    break
            except (json.JSONDecodeError, ValueError, AttributeError):
                continue

        # フォールバック: timeタグから
        if not published_at:
            time_tag = soup.find('time', class_='article_date')
            if time_tag and time_tag.get('datetime'):
                try:
                    published_at = datetime.fromisoformat(
                        time_tag['datetime'].replace('Z', '+00:00')
                    )
                except (ValueError, AttributeError):
                    pass

        # 本文取得
        body_parts = []
        # 記事本文を探す
        article_body = soup.find('div', class_='article_body')
        if not article_body:
            # フォールバック
            article_body = soup.find('article')

        if article_body:
            for p in article_body.find_all('p'):
                text = p.get_text(strip=True)
                if text and len(text) > 10:  # 短すぎるものは除外
                    body_parts.append(text)

        body = '\n\n'.join(body_parts) if body_parts else ""

        return ParsedArticle(
            url=url,
            title=title or "タイトル不明",
            published_at=published_at,
            body=body or "本文取得失敗"
        )


def is_nifty_news_url(url: str) -> bool:
    """@niftyニュースのURLか判定（モジュールレベル関数）"""
    return NiftyNewsParser.is_nifty_news_url(url)
