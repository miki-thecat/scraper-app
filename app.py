import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import safe_str_cmp
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
        if not auth_header or not auth_header.staartswith("Basic "):
            return False
        try:
            encoded = auth_header.split(" ")[1]
            userpass = b64decode(encoded).decode("utf-8")
            username, password  = userpass.split(":", 1)
            return safe_str_cmp(username, USER) and safe_str_cmp(password, PASS)
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

    #----------- ルーティング設定 -----------

    @app.route('./')
    @requires_basic_auth
    def index():
        articles = Article.query.order_by(Article.id.desc()).all()
        return render_template("index.html", articles=articles)

    


