import time
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import json
import shlex
import subprocess

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


YAHOO_DOMAIN = "news.yahoo.co.jp"


# Dev Container でインストール済みの Chromium / chromedriver のパス
CHROMIUM_BINARY = "/usr/bin/chromium"
CHROMEDRIVER_BINARY = "/usr/bin/chromedriver"

# ChromeDriver を自動操作するためのドライバを生成する
def _build_driver() -> webdriver.Chrome:
    options = Options()
    options.binary_location = CHROMIUM_BINARY
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=ja-JP")
    service = Service(CHROMEDRIVER_BINARY)
    return webdriver.Chrome(service=service, options=options)


def fetch_html_with_selenium(url: str) -> str:
    """
    Seleniumを使い、指定されたURLの動的HTMLソースを取得する。

    JavaScriptでレンダリングされるコンテンツを含むページから、
    最終的なHTMLを取得するために使用する。

    Args:
        url: 取得対象のWebページのURL。

    Returns:
        レンダリング後のHTMLソースコード。
    """
    driver = _build_driver()
    # エラー発生時も確実にブラウザを終了させ、リソースリークを防ぐ
    try:
        driver.get(url)
        # JSによる動的コンテンツの描画を待つための固定ウェイト。
        # より堅牢にするには、特定の要素が表示されるまで待つExplicit Waitが推奨される。
        time.sleep(2)
        final_url = driver.current_url
        html = driver.page_source
        return final_url, html
    finally:
        driver.quit()


# NHK の記事をスクレイピングする
def scrape_nhk_article(url: str) -> dict:
    parsed = urlparse(url)  # URLをパースに分解
    if "nhk.or.jp" not in parsed.netloc:  # https://www3.nhk.or.jp/news/
        raise ValueError("NHKニュースのURLを指定してください")

    driver = _build_driver()
    try:
        driver.get(url)

        # ページの読み込みを待機
        time.sleep(2)
        final_url = driver.current_url

        # 追加でレンダリング待機
        time.sleep(0.7)
        html = driver.page_source
    finally:
        driver.quit()

    soup = BeautifulSoup(html, "html.parser")

    # タイトルを推定
    title = None
    for sel in ["h1#content--title", "h1", "header h1"]:
        node = soup.select_one(sel)
        if node and node.get_text(strip=True):
            title = node.get_text(strip=True)
            break
    if not title:
        title = soup.title.get_text(strip=True) if soup.title else "(タイトル不明)"

    # 日時指定
    published = None
    for sel in ["time[datetime]", "p.content--date-time", "time"]:
        node = soup.select_one(sel)
        if node and node.get_text(strip=True):
            published = node.get_text(strip=True)
            break

    # 本文を推定
    body_parts = []
    for sel in ["div#content--story p", "article p", "div.main__body p"]:
        ps = soup.select(sel)
        if ps:
            body_parts = [p.get_text(strip=True)
                          for p in ps if p.get_text(strip=True)]
            if body_parts:
                break
    body = "\n".join(body_parts) if body_parts else "(本文を取得できませんでした)"

    return {
        "url": final_url,
        "title": title,
        "published": published,
        "body": body,
    }

def scrape_yahoo_article(url: str) -> dict:
    """
    Yahoo!ニュースの記事を伝統的な方法でスクレイピングする。
    AIを使わず、BeautifulSoupでHTMLを直接解析する。
    """
    if YAHOO_DOMAIN not in url:
        raise ValueError("Yahoo!ニュースのURLを指定してください")

    final_url, html = fetch_html_with_selenium(url)
    soup = BeautifulSoup(html, "html.parser")

    # タイトルを抽出
    title_node = soup.select_one('article header h1')
    title = title_node.get_text(strip=True) if title_node else "(タイトル不明)"

    # 公開日時を抽出
    published_node = soup.select_one('time')
    published = published_node.get_text(strip=True) if published_node else None

    # 本文を抽出
    article_body_div = soup.select_one('div.article_body')
    body = "(本文を取得できませんでした)"
    if article_body_div:
        # 本文内のすべてのpタグからテキストを抽出
        body_parts = [p.get_text(strip=True) for p in article_body_div.select('p')]
        # 空の段落をフィルタリングして結合
        body = "\n".join(part for part in body_parts if part)

    # 既存のArticleモデルの形式に合わせて返す
    return {
        "final_url": final_url,
        "title": title,
        "published_at": published,
        "body": body,
    }
# --- 追記ここまで ---

# テスト用
if __name__ == "__main__":
    url = "https://news.yahoo.co.jp/articles/d876ec47c12ceadcc09367d70c6af194f73e3929"
    from pprint import pprint
    pprint(scrape_yahoo_article(url))

