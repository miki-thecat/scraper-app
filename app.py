import os
from flask import Flask, render_template, request, redirect, url_for, flash
import hmac
from models import db, Article, init_db
from scraper import scrape_nhk_article
from config import Config
from functools import wraps
from base64 import b64decode


def create_app():
    app = Flask(__name__, static_folder='static', template_folder="templates")
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    # DB 初期化
    db.init_app(app)
    with app.app_context():
        init_db()

    # Basic認証 AUTH
    USER = os.getenv("BASIC_AUTH_USERNAME", "admin")
    PASS = os.getenv("BASIC_AUTH_PASSWORD", "password")

    def check_auth(auth_header: str) -> bool:
        if not auth_header or not auth_header.startswith("Basic "):
            return False
        try:
            encoded = auth_header.split(" ")[1]
            userpass = b64decode(encoded).decode("utf-8")
            username, password = userpass.split(":", 1)
            return hmac.compare_digest(username, USER) and hmac.compare_digest(password, PASS)
        except Exception:
            return False

    def requires_basic_auth(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization")
            if not check_auth(auth):
                return ("Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="Restricted"'})
            return f(*args, **kwargs)
        return wrapper

    # ----------- ルーティング設定 -----------

    @app.get("/")
    @requires_basic_auth
    def index():
        articles = Article.query.order_by(Article.id.desc()).all()
        return render_template("index.html", articles=articles)

    @app.post("/scrape")
    @requires_basic_auth
    def scrape():
        url = request.form.get("url", "").strip()
        if not url:
            flash("URLを入力してください", "error")
            return redirect(url_for("index"))

        try:
            data = scrape_nhk_article(url)
            # 既存のURLは更新, なければ作成
            art = Article.query.filter_by(url=data["final_url"]).first()
            if not art:  # 新規作成
                # DBモデル作成
                art = Article(
                    url=data["final_url"],
                    title=data["title"],
                    published_at=data["published_at"],
                    body=data["data"],
                )
                db.session.add(art)  # DB追加
            else:  # 更新
                art.title = data["title"]
                art.published_at = data["published_at"]
                art.body = data["data"]
            db.session.commit()  # DB保存
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"記事の取得に失敗しました: {e}", "error")
            return redirect(url_for("index"))  # エラーハンドリング

    return app  # Flaskアプリケーションを返す


app = create_app()

if __name__ == "__main__":
    # Dev Container でポート転送される想定
    app.run(host="0.0.0.0", port=8000, debug=False)
