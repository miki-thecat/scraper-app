import os


class Config:
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'change_me_secret')

    # DB接続
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///articles.db"
    )

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # 接続が切れている場合に自動的に再接続する
    }

    SQLALCHEMY_TRACK_MODIFICATIONS = False  # 無駄な警告をやめる
