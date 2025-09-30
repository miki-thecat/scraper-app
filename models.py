from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from sqlalchemy.types import DateTime, String, Integer, Text

db = SQLAlchemy()


class Article(db.Model):
    __tablename__ = "articles"

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    url = db.Column(String(512), nullable=False)
    title = db.Column(String(512), nullable=False)
    published_at = db.Column(String(128), nullable=True)  # NHKの表示文字列をそのまま格納
    body = db.Column(Text, nullable=False)
    ccreated_at = db.Column(DateTime(timezone=True),
                            default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("url", name="uq_articles_url"),
    )


def init_db():
    db.create_all()
