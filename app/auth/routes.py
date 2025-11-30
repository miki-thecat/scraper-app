from __future__ import annotations

from urllib.parse import urljoin, urlparse

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.models.db import db
from app.models.user import User

from . import session_manager


auth_bp = Blueprint("auth", __name__)


def _is_safe_redirect(target: str | None) -> bool:
    if not target:
        return False
    base = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    return test.scheme in {"http", "https"} and base.netloc == test.netloc


def _next_url() -> str:
    target = request.args.get("next") or request.form.get("next")
    if target and _is_safe_redirect(target):
        return target
    return url_for("main.index")


@auth_bp.get("/login")
def login():
    if session_manager.is_authenticated():
        return redirect(url_for("main.index"))

    next_url = request.args.get("next") if _is_safe_redirect(request.args.get("next")) else None
    return render_template("login.html", next_url=next_url)


@auth_bp.post("/login")
def login_post():
    if session_manager.is_authenticated():
        return redirect(url_for("main.index"))

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    next_param = request.form.get("next")
    next_query = {"next": next_param} if _is_safe_redirect(next_param) else {}

    if not username or not password:
        flash("ユーザー名とパスワードを入力してください。", "error")
        return redirect(url_for("auth.login", **next_query))

    user = User.query.filter_by(username=username).first()
    if not user or not user.verify_password(password):
        flash("ユーザー名またはパスワードが正しくありません。", "error")
        return redirect(url_for("auth.login", **next_query))

    session_manager.login_user(user)
    flash("ログインしました。", "success")
    return redirect(_next_url())


@auth_bp.post("/logout")
def logout():

    if session_manager.is_authenticated():
        session_manager.logout_user()
        flash("ログアウトしました。", "success")
    return redirect(url_for("auth.login"))


@auth_bp.get("/register")
def register():
    if session_manager.is_authenticated():
        return redirect(url_for("main.index"))

    next_url = request.args.get("next") if _is_safe_redirect(request.args.get("next")) else None
    return render_template("register.html", next_url=next_url)


@auth_bp.post("/register")
def register_post():
    if session_manager.is_authenticated():
        return redirect(url_for("main.index"))

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")

    next_param = request.form.get("next")
    next_query = {"next": next_param} if _is_safe_redirect(next_param) else {}

    if not username or not password:
        flash("ユーザー名とパスワードは必須です。", "error")
        return redirect(url_for("auth.register", **next_query))
    if len(username) < 3:
        flash("ユーザー名は3文字以上で入力してください。", "error")
        return redirect(url_for("auth.register", **next_query))
    if password != confirm:
        flash("パスワードが一致しません。", "error")
        return redirect(url_for("auth.register", **next_query))
    if len(password) < 6:
        flash("パスワードは6文字以上にしてください。", "error")
        return redirect(url_for("auth.register", **next_query))

    existing = User.query.filter_by(username=username).first()
    if existing:
        flash("そのユーザー名は既に利用されています。", "error")
        return redirect(url_for("auth.register", **next_query))

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    session_manager.login_user(user)
    flash("アカウントを作成しログインしました。", "success")
    return redirect(_next_url())
