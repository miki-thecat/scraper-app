import pytest
import os
from scraper import create_app
from config import TestConfig
from scraper.models import db, Article
from datetime import datetime
import base64

@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app

@pytest.fixture
def client(app):
    with app.test_client() as client:
        with app.app_context():
            yield client

@pytest.fixture
def auth_headers():
    return {
        'Authorization': 'Basic ' + base64.b64encode(b"test:test").decode('utf-8')
    }

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert "スクレイピングアプリケーション".encode('utf-8') in response.data

def test_scrape_success_nhk(client, mocker, app, auth_headers):
    mock_data = {
        "url": "https://www3.nhk.or.jp/news/html/20240101/mock-article.html",
        "title": "NHKテスト記事",
        "body": "これはNHKのテスト本文です。",
        "posted_at": datetime.now()
    }
    mock_nhk = mocker.patch('scraper.routes.scrape_nhk_article', return_value=mock_data)
    mock_yahoo = mocker.patch('scraper.routes.scrape_yahoo_article')

    response = client.post('/scrape', data={'url': mock_data["url"]}, headers=auth_headers)

    assert response.status_code == 302
    assert response.location == "/"
    mock_nhk.assert_called_once()
    mock_yahoo.assert_not_called()

    with app.app_context():
        article = Article.query.filter_by(url=mock_data["url"]).first()
        assert article is not None
        assert article.title == mock_data["title"]


def test_scrape_success_yahoo(client, mocker, app, auth_headers):
    mock_data = {
        "url": "https://news.yahoo.co.jp/articles/mock-article",
        "title": "Yahooテスト記事",
        "body": "これはYahooのテスト本文です。",
        "posted_at": datetime.now()
    }
    mock_nhk = mocker.patch('scraper.routes.scrape_nhk_article')
    mock_yahoo = mocker.patch('scraper.routes.scrape_yahoo_article', return_value=mock_data)

    response = client.post('/scrape', data={'url': mock_data["url"]}, headers=auth_headers)

    assert response.status_code == 302
    assert response.location == "/"
    mock_yahoo.assert_called_once()
    mock_nhk.assert_not_called()

    with app.app_context():
        article = Article.query.filter_by(url=mock_data["url"]).first()
        assert article is not None
        assert article.title == mock_data["title"]

def test_scrape_auth_failure(client):
    response = client.post('/scrape', data={'url': 'http://example.com/article1'})
    assert response.status_code == 401

def test_scrape_no_url(client, auth_headers):
    response = client.post('/scrape', data={'url': ''}, headers=auth_headers)
    
    assert response.status_code == 302
    assert response.location == "/"

    response_redirect = client.get('/')
    assert "URLを入力してください".encode('utf-8') in response_redirect.data
