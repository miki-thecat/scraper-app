import base64
import pytest

from app import create_app
from app.config import TestConfig
from app.models.db import db


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_header(app):
    credentials = f"{app.config['BASIC_AUTH_USERNAME']}:{app.config['BASIC_AUTH_PASSWORD']}".encode()
    token = base64.b64encode(credentials).decode()
    return {"Authorization": f"Basic {token}"}
