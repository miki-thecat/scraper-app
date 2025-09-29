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
    service= Service(CHROMEDRIVER_BINARY)
    return webdriver.Chrome(service=service, options=options)



