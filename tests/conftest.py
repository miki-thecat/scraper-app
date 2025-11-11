import base64
import pytest

from app import create_app
from app.config import TestConfig
from app.models.db import db
from app.models.user import User


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        app.config["ENABLED_FEED_PROVIDERS"] = ("yahoo",)
        default_username = app.config["BASIC_AUTH_USERNAME"]
        default_password = app.config["BASIC_AUTH_PASSWORD"]
        user = db.session.scalar(db.select(User).where(User.username == default_username))
        if user is None:
            user = User(username=default_username)
            user.set_password(default_password)
            db.session.add(user)
            db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_header(app):
    credentials = f"{app.config['BASIC_AUTH_USERNAME']}:{app.config['BASIC_AUTH_PASSWORD']}".encode()
    token = base64.b64encode(credentials).decode()
    return {"Authorization": f"Basic {token}"}
