from flask import Flask
from config import Config

def create_app(config_class=Config):
    """アプリケーションファクトリ"""
    app = Flask(__name__, instance_relative_config=True, template_folder='../templates')

    app.config.from_object(config_class)

    from .models import db, init_db
    db.init_app(app)
    with app.app_context():
        init_db(app)

    # 3. ルーティング(Blueprint)を登録する
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # 認証のためにappコンテキストを渡す
    from .routes import check_auth

    return app
