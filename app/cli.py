from __future__ import annotations

from flask import Flask


def register_cli_commands(app: Flask) -> None:
    """Flask CLIに便利コマンドを登録。"""

    @app.cli.command("list-articles")
    def list_articles() -> None:  # pragma: no cover - CLIユーティリティ
        """DB内の記事IDとタイトルを列挙。"""
        from .models.article import Article
        from .models.db import db

        with app.app_context():
            for article in db.session.query(Article).order_by(Article.created_at.desc()).all():
                print(f"{article.id}\t{article.title}")
