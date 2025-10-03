from flask import Flask

def create_app():
    """アプリケーションファクトリ"""
    app = Flask(__name__, instance_relative_config=True, template_folder='../templates')

    # 1. 設定を読み込む
    app.config.from_object('config.Config')

    # 2. データベースを初期化する
    from .models import db, init_db
    db.init_app(app)
    init_db(app)

    # 3. ルーティング(Blueprint)を登録する
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
