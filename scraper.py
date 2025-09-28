import time
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Dev Container でインストール済みの Chromium / chromedriver のパス
CHROMIUM_BINARY = "/usr/bin/chromium"
CHROMEDRIVER_BINARY = "/usr/bin/chromedriver"

def _build_driver() -> webdriver.Chrome:
    Options = Options()
    

