"""
@niftyニュース専用のスクレイピング/パース処理
"""
from __future__ import annotations

import json
import re
from datetime import datetime

from bs4 import BeautifulSoup
from flask import current_app

from .parsing import ParsedArticle


class NiftyNewsParser:
    """@niftyニュース記事の解析"""

    BASE_URL = "https://news.nifty.com"

    @staticmethod
    def is_nifty_news_url(url: str) -> bool:
        """@niftyニュースのURLか判定（topics または article）"""
        return (
            url.startswith("https://news.nifty.com/topics/") or
            url.startswith("https://news.nifty.com/article/")
        )

    @staticmethod
    def extract_article_url(html: str) -> str | None:
        """トピックスページから記事URLを抽出"""
        soup = BeautifulSoup(html, 'lxml')
        
        # article_urlメタタグから取得
        meta_tag = soup.find('meta', attrs={'name': 'article_url'})
        if meta_tag and meta_tag.get('content'):
            return meta_tag['content']
        
        # article_moreリンクから取得
        more_link = soup.find('a', href=re.compile(r'/article/'))
        if more_link and more_link.get('href'):
            href = more_link['href']
            if href.startswith('/'):
                return f"{NiftyNewsParser.BASE_URL}{href}"
            return href
        
        return None

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

        # JSON-LDから情報取得（最優先）
        title = None
        published_at = None
        description = None
        
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                if not script.string:
                    continue
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'NewsArticle':
                    title = data.get('headline')
                    if data.get('datePublished'):
                        try:
                            published_at = datetime.fromisoformat(
                                data['datePublished'].replace('Z', '+00:00')
                            )
                        except (ValueError, AttributeError):
                            pass
                    description = data.get('description', '')
                    break
            except (json.JSONDecodeError, ValueError, AttributeError) as e:
                current_app.logger.debug(f"JSON-LD parse error: {e}")
                continue

        # タイトルフォールバック
        if not title:
            # Open Graphから取得
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title['content'].replace('｜ニフティニュース', '').strip()
            
            # h1から取得
            if not title:
                h1_tag = soup.find('h1')
                if h1_tag:
                    title = h1_tag.get_text(strip=True)

        # 本文取得
        body_parts = []
        
        # article_body_text から取得
        article_body = soup.find('div', class_='article_body_text')
        if article_body:
            # id="article_body_text_sentence" 内の <p> タグを取得
            sentence_div = article_body.find('div', id='article_body_text_sentence')
            if sentence_div:
                for p in sentence_div.find_all('p', recursive=True):
                    text = p.get_text(strip=True)
                    # リンクテキストやキーワードを除外
                    if text and len(text) > 15 and not text.startswith('【'):
                        body_parts.append(text)
        
        # フォールバック: article タグ内のpタグ
        if not body_parts:
            article_tag = soup.find('article', class_='article')
            if article_tag:
                for p in article_tag.find_all('p'):
                    text = p.get_text(strip=True)
                    if text and len(text) > 15:
                        body_parts.append(text)

        body = '\n\n'.join(body_parts) if body_parts else description or ""

        return ParsedArticle(
            url=url,
            title=title or "タイトル不明",
            published_at=published_at,
            body=body or "本文取得失敗"
        )


def is_nifty_news_url(url: str) -> bool:
    """@niftyニュースのURLか判定（モジュールレベル関数）"""
    return NiftyNewsParser.is_nifty_news_url(url)
