import pytest
from scraper import create_app

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", # メモリ上のDBを使う
        "WTF_CSRF_ENABLED": False, # テストではCSRF保護を無効化
        "BASIC_AUTH_USERNAME": "test",
        "BASIC_AUTH_PASSWORD": "test",
    })

    with app.app_context():
        from scraper.models import db, init_db
        init_db(app)

    yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

def test_index_page(client):
    """トップページが正常に表示されるかテストする"""
    response = client.get('/')
    assert response.status_code == 200
    assert "スクレイピングアプリケーション".encode('utf-8') in response.data