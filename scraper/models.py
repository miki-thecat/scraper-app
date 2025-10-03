from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect

# 1. appと紐付けずに、dbオブジェクトだけを先に作成する
db = SQLAlchemy()

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    posted_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<Article {self.title}>"

# 2. appを受け取って、データベースの初期化を行う関数を定義
def init_db(app):
    with app.app_context():
        # テーブルが存在しない場合のみ作成する
        inspector = inspect(db.engine)
        if not inspector.has_table("article"):
            db.create_all()