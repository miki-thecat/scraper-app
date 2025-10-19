from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def init_db(app) -> None:
    """アプリケーション初期化時にテーブルを作成。"""
    with app.app_context():
        # db.create_all()  # Handled by Flask-Migrate
        pass
