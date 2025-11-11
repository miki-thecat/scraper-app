from __future__ import annotations

from collections import defaultdict, deque
from time import time
from typing import DefaultDict

from flask import Flask, jsonify, request
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from .config import Config
from .models.db import db, init_db
from .auth import session_manager

csrf = CSRFProtect()


def create_app(config_class: type[Config] | None = None) -> Flask:
    """Flaskアプリケーションファクトリ。"""

    app = Flask(__name__, template_folder="templates", static_folder="static")

    config_class = config_class or Config
    app.config.from_object(config_class)

    db.init_app(app)
    init_db(app)
    Migrate(app, db)
    csrf.init_app(app)

    from .auth.routes import auth_bp
    from .routes import api_bp, bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    csrf.exempt(api_bp)

    # CLI登録
    from .cli import register_cli_commands

    register_cli_commands(app)

    _init_rate_limiter(app)
    _init_security_headers(app)
    _init_csrf_error_handler(app)

    @app.context_processor
    def _inject_auth_state() -> dict[str, object]:
        return {
            "is_authenticated": session_manager.is_authenticated(),
            "auth_username": session_manager.current_username(),
        }

    return app


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


def _init_security_headers(app: Flask) -> None:
    """セキュリティヘッダーを設定"""

    @app.after_request
    def _add_security_headers(response):
        # Content Security Policy - XSS対策
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )

        # クリックジャッキング対策
        response.headers['X-Frame-Options'] = 'DENY'

        # MIMEタイプスニッフィング対策
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # XSS Protection（古いブラウザ用）
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # HTTPS強制（本番環境のみ）
        if app.config.get('FLASK_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains'
            )

        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions Policy（旧Feature Policy）
        response.headers['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=()'
        )

        return response


def _init_csrf_error_handler(app: Flask) -> None:
    """CSRFエラー時のカスタムハンドラを設定"""
    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        app.logger.warning(f'CSRF validation failed: {e.description}')
        return jsonify({
            'error': 'セキュリティ上の理由により、リクエストが拒否されました。',
            'details': e.description
        }), 400
