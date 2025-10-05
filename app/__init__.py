from __future__ import annotations

from flask import Flask

from .config import Config
from .models.db import db, init_db


def create_app(config_class: type[Config] | None = None) -> Flask:
    """Flaskアプリケーションファクトリ。"""

    app = Flask(__name__, template_folder="templates", static_folder="static")

    config_class = config_class or Config
    app.config.from_object(config_class)

    db.init_app(app)
    init_db(app)

    from .routes import api_bp, bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # CLI登録
    from .cli import register_cli_commands

    register_cli_commands(app)

    return app
