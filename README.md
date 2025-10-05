# Scraper App

Yahoo!ニュースの記事をスクレイピングし、AIでリスク評価を行うFlaskアプリケーションです。

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` にデータベースURLやOpenAI APIキーを設定してください。

ローカルで起動するには以下を実行します。

```bash
flask --app app.main run
```

## テスト

```bash
pytest
```

## MLモデルの再学習

```bash
python ml/train.py --train ml/data/train.csv --valid ml/data/valid.csv
python ml/evaluate.py --valid ml/data/valid.csv
```

`ml/data/` 配下にサンプルの学習/検証データを同梱しています。必要に応じて追記・差し替えしてください。

## デプロイ

`deploy/` ディレクトリにNginx設定、systemdユニット、CodeBuild用`buildspec.yml`を用意しています。AWS EC2 + RDS構成を想定しています。
