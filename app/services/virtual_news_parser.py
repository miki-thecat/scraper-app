from __future__ import annotations

import logging
from datetime import datetime

from bs4 import BeautifulSoup

from .parsing import ParsedArticle

logger = logging.getLogger(__name__)

class VirtualNewsParser:
    """Virtual News記事の解析"""

    @staticmethod
    def is_virtual_news_url(url: str) -> bool:
        """Virtual NewsのURLか判定"""
        return "virtual-news/article/" in url

    @staticmethod
    def parse_article(html: str, url: str) -> ParsedArticle:
        """
        Virtual News記事をパース

        Args:
            html: HTML文字列
            url: 記事URL

        Returns:
            ParsedArticle: パース結果
        """
        soup = BeautifulSoup(html, 'lxml')

        # タイトル取得
        title_tag = soup.find('h1', class_='blog-post-title')
        title = title_tag.get_text(strip=True) if title_tag else "タイトル不明"

        # 日付取得
        published_at = None
        date_tag = soup.find('p', class_='blog-post-meta')
        if date_tag:
            date_str = date_tag.get_text(strip=True)
            try:
                # 2025年11月30日 10:00 -> datetime
                published_at = datetime.strptime(date_str, '%Y年%m月%d日 %H:%M')
            except ValueError:
                pass

        # 本文取得
        body_parts = []
        article_body = soup.find('div', class_='article_body')
        if article_body:
            for p in article_body.find_all('p'):
                text = p.get_text(strip=True)
                if text:
                    body_parts.append(text)

        body = '\n\n'.join(body_parts) if body_parts else "本文取得失敗"

        return ParsedArticle(
            url=url,
            title=title,
            published_at=published_at,
            body=body
        )
