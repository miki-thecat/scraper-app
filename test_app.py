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

def test_scrape_success(client, mocker, app, auth_headers):
    mock_data = {
        "url": "http://example.com/article1",
        "title": "テスト記事",
        "body": "これはテスト記事の本文です。",
        "posted_at": datetime.now()
    }
    mocker.patch('scraper.routes.scrape_nhk_article', return_value=mock_data)

    response = client.post('/scrape', data={'url': 'http://example.com/article1'}, headers=auth_headers)

    assert response.status_code == 302
    assert response.location == "/"

    with app.app_context():
        article = Article.query.filter_by(url="http://example.com/article1").first()
        assert article is not None
        assert article.title == "テスト記事"

def test_scrape_auth_failure(client):
    response = client.post('/scrape', data={'url': 'http://example.com/article1'})
    assert response.status_code == 401

def test_scrape_no_url(client, auth_headers):
    response = client.post('/scrape', data={'url': ''}, headers=auth_headers)
    
    assert response.status_code == 302
    assert response.location == "/"

    response_redirect = client.get('/')
    assert "URLを入力してください".encode('utf-8') in response_redirect.data
