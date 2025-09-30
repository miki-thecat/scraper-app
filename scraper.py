import time
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

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

    soup = BeautifulSoup(html, "htmk.parser")

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
