from __future__ import annotations

from app.models.user import User
from app.models.db import db


def test_register_creates_user(app, client):
    app.config["WTF_CSRF_ENABLED"] = False

    resp = client.post(
        "/register",
        data={
            "username": "newuser",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=False,
    )

    assert resp.status_code == 302
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.username == "newuser"))
        assert user is not None


def test_login_with_registered_user(app, client):
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        user = User(username="loginuser")
        user.set_password("secret123")
        db.session.add(user)
        db.session.commit()

    resp = client.post(
        "/login",
        data={"username": "loginuser", "password": "secret123"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
