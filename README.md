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

## API エンドポイント

すべてのエンドポイントは Basic 認証（`.env` で設定）または Bearer トークン (`API_ACCESS_TOKENS`) のいずれかで認証する必要があります。レート制限は `RATE_LIMIT_PER_MINUTE`（デフォルト 60 req/min）で制御できます。

| メソッド | パス | 説明 |
| --- | --- | --- |
| `GET` | `/api/articles` | 記事の一覧。`q`/`start`/`end`/`page`/`per_page` で絞り込み・ページング可能。|
| `GET` | `/api/articles/<article_id>` | 単一記事の詳細を取得。|
| `POST` | `/api/articles` | スクレイピングして記事を作成。`force` で再スクレイプ、`run_ai`/`force_ai` で AI の実行制御が可能。|

リクエスト例:

```bash
# Basic 認証
curl -u admin:password -X POST \
  -H "Content-Type: application/json" \
  -d '{"url": "https://news.yahoo.co.jp/articles/example", "force_ai": true}' \
  http://localhost:5000/api/articles

# Bearer トークン
curl -H "Authorization: Bearer my-token" \
  http://localhost:5000/api/articles
```

## デプロイ

`deploy/` ディレクトリにNginx設定、systemdユニット、CodeBuild用`buildspec.yml`を用意しています。AWS EC2 + RDS構成を想定しています。

`deploy/deploy.sh` は CodeBuild から呼び出され、アプリを `build/app.tar.gz` にパッケージし、`EC2_HOST` が設定されている場合は SCP + systemd 再起動で EC2 に反映します。
