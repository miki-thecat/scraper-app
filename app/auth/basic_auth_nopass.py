"""開発時の簡易Basic認証ミドルウェア。

本番ではNginx側で同等の認証を掛ける想定。
"""
from __future__ import annotations

from base64 import b64decode
from functools import wraps
from typing import Callable, TypeVar

from flask import Response, current_app, request

T = TypeVar("T")


def requires_basic_auth(view: Callable[..., T]) -> Callable[..., T]:
    @wraps(view)
    def wrapped(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not _is_authorized(auth):
            resp = Response("Unauthorized", status=401)
            resp.headers["WWW-Authenticate"] = 'Basic realm="Restricted"'
            return resp
        return view(*args, **kwargs)

    return wrapped


def _is_authorized(auth_header: str | None) -> bool:
    if not auth_header or not auth_header.startswith("Basic "):
        return False
    try:
        username, password = b64decode(auth_header.split(" ", 1)[1]).decode("utf-8").split(":", 1)
    except Exception:
        return False

    return (
        username == current_app.config.get("BASIC_AUTH_USERNAME")
        and password == current_app.config.get("BASIC_AUTH_PASSWORD")
    )
