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

    expected_username = current_app.config.get("BASIC_AUTH_USERNAME", "")
    expected_password = current_app.config.get("BASIC_AUTH_PASSWORD", "")

    if username != expected_username or password != expected_password:
        flash("ユーザー名またはパスワードが正しくありません。", "error")
        return redirect(url_for("auth.login", **next_query))

    session_manager.login_user(username)
    flash("ログインしました。", "success")
    return redirect(_next_url())


@auth_bp.post("/logout")
def logout():
    if session_manager.is_authenticated():
        session_manager.logout_user()
        flash("ログアウトしました。", "success")
    return redirect(url_for("auth.login"))
