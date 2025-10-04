import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change_me_secret')
    BASIC_AUTH_USERNAME = os.getenv("BASIC_AUTH_USERNAME", "admin")
    BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "password")
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///local.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class TestConfig(Config):
    TESTING = True
    BASIC_AUTH_USERNAME = 'test'
    BASIC_AUTH_PASSWORD = 'test'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'