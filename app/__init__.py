from __future__ import annotations

from collections import defaultdict, deque
from time import time

from flask import Flask, jsonify, request

from .config import Config
from .models.db import db, init_db
from .auth import session_manager


def create_app(config_class: type[Config] | None = None) -> Flask:
    """Flaskアプリケーションファクトリ。"""

    app = Flask(__name__, template_folder="templates", static_folder="static")

    config_class = config_class or Config
    app.config.from_object(config_class)

    db.init_app(app)
    init_db(app)

    from .auth.routes import auth_bp
    from .routes import api_bp, bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # CLI登録
    from .cli import register_cli_commands

    register_cli_commands(app)

    _init_rate_limiter(app)

    @app.context_processor
    def _inject_auth_state() -> dict[str, object]:
        return {
            "is_authenticated": session_manager.is_authenticated(),
            "auth_username": session_manager.current_username(),
        }

    return app


from typing import DefaultDict


_RATE_BUCKETS: DefaultDict[tuple[str, str], deque[float]] = defaultdict(deque)


def _rate_limit_key() -> tuple[str, str]:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        ip = forwarded.split(",", 1)[0].strip()
    else:
        ip = request.remote_addr or ""
    auth_header = request.headers.get("Authorization")
    if auth_header:
        credential = auth_header.strip()
    else:
        api_key = request.headers.get("X-API-Key", "").strip()
        credential = f"api:{api_key}" if api_key else ""
    return ip, credential


def _init_rate_limiter(app: Flask) -> None:
    window = 60.0

    @app.before_request
    def _apply_rate_limit():
        limit_per_minute = app.config.get("RATE_LIMIT_PER_MINUTE", 60)
        if limit_per_minute <= 0:
            return None
        if request.blueprint != "api":
            return None

        key = _rate_limit_key()
        bucket = _RATE_BUCKETS[key]
        now = time()

        while bucket and now - bucket[0] > window:
            bucket.popleft()

        if len(bucket) >= limit_per_minute:
            return jsonify({"error": "Too Many Requests"}), 429

        bucket.append(now)
        return None
