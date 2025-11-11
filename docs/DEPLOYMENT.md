## テスト

### テストスイート実行

```bash
# 全テスト実行
pytest

# 詳細表示
pytest -v

# カバレッジ計測
pytest --cov=app --cov-report=term-missing

# HTMLレポート生成
pytest --cov=app --cov-report=html
open htmlcov/index.html

# 特定テストのみ実行
pytest tests/test_routes.py
pytest tests/test_nifty_news.py -k "test_parse"
```

### テスト構成

```
tests/
├── test_ai.py              # AI推論テスト
├── test_analytics.py       # メトリクス集計テスト
├── test_api.py             # REST API テスト
├── test_auth.py            # 認証テスト
├── test_cli.py             # CLI コマンドテスト
├── test_csrf.py            # CSRF保護テスト
├── test_ml.py              # 機械学習テスト
├── test_news_feed.py       # RSS取得テスト
├── test_nifty_news.py      # @niftyニュースパーサーテスト
├── test_parsing.py         # Yahoo!ニュースパーサーテスト
├── test_risk.py            # リスク分類テスト
├── test_routes.py          # ルーティング・UI テスト
├── test_scraping.py        # スクレイピングエンジンテスト
└── test_security.py        # セキュリティヘッダーテスト
```

### カバレッジ

- **総合カバレッジ**: 80%+
- **コアサービス**: 90%+
- **クリティカルパス**: 100%

## コード品質

### Linting

```bash
# Ruff (高速Pythonリンター)
ruff check .
ruff check --fix .  # 自動修正

# Black (フォーマッター)
black .
black --check .  # チェックのみ

# isort (インポート順序)
isort .
isort --check-only .

# mypy (型チェック)
mypy app/
```

### Security Scan

```bash
# Bandit (セキュリティ脆弱性)
bandit -r app/ -ll

# Safety (依存関係の脆弱性)
safety check

# Trivy (コンテナスキャン)
trivy fs .
```

## デプロイ

### Docker

```bash
# イメージビルド
docker build -t scraper-app:latest .

# コンテナ実行
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e OPENAI_API_KEY=sk-... \
  scraper-app:latest

# Docker Compose
docker-compose up -d
docker-compose logs -f
docker-compose down
```

### 本番環境 (Gunicorn + Nginx)

**1. Gunicorn 設定** (`gunicorn.conf.py`):
```python
bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
timeout = 120
accesslog = "-"
errorlog = "-"
```

**2. 起動**:
```bash
gunicorn -c gunicorn.conf.py "app:create_app()"
```

**3. Nginx リバースプロキシ**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/scraper-app/app/static;
        expires 30d;
    }
}
```

### Systemd サービス

`/etc/systemd/system/scraper-app.service`:
```ini
[Unit]
Description=Scraper App
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/scraper-app
Environment="PATH=/var/www/scraper-app/venv/bin"
EnvironmentFile=/var/www/scraper-app/.env
ExecStart=/var/www/scraper-app/venv/bin/gunicorn -c gunicorn.conf.py "app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

起動:
```bash
sudo systemctl daemon-reload
sudo systemctl enable scraper-app
sudo systemctl start scraper-app
sudo systemctl status scraper-app
```

### 環境変数 (本番)

```bash
FLASK_ENV=production
DATABASE_URL=postgresql://user:pass@localhost:5432/scraper_db
SECRET_KEY=<strong-random-key>
OPENAI_API_KEY=sk-...
BASIC_AUTH_USERNAME=admin
BASIC_AUTH_PASSWORD=<secure-password>
ENABLE_AI=true
RATE_LIMIT_PER_MINUTE=60
```

## CI/CD

### GitHub Actions

- **Trigger**: Push to `main`, `develop`, PRs
- **Jobs**: Test, Lint, Security Scan, Build, Deploy

詳細は [CI/CD.md](docs/CI_CD.md) を参照。

### ワークフロー

1. **Test**: Python 3.11, 3.12 でテスト実行
2. **Lint**: Ruff, Black, isort, mypy
3. **Security**: Trivy, Bandit, Safety
4. **Build**: Docker イメージビルド (amd64, arm64)
5. **Deploy**: 本番環境へ自動デプロイ (main ブランチのみ)

### バッジ

[![CI/CD](https://github.com/YOUR_USERNAME/scraper-app/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/YOUR_USERNAME/scraper-app/actions)
[![Coverage](https://codecov.io/gh/YOUR_USERNAME/scraper-app/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/scraper-app)

## トラブルシューティング

### データベース接続エラー

```bash
# PostgreSQL 起動確認
sudo systemctl status postgresql

# 接続テスト
psql -U postgres -h localhost -d scraper_db

# マイグレーション再実行
flask db upgrade
```

### OpenAI API エラー

```python
# エラー: "Invalid API key"
# → .env の OPENAI_API_KEY を確認

# エラー: "Rate limit exceeded"
# → API使用量を確認、プラン変更を検討

# エラー: "Model not found"
# → config.py の AI_MODEL を "gpt-4" から "gpt-3.5-turbo" に変更
```

### スクレイピング失敗

```python
# タイムアウト
# → REQUEST_TIMEOUT を増やす (config.py)

# パースエラー
# → ニュースサイトの構造変更の可能性
# → parsing.py / nifty_news.py を更新
```

## 貢献

Pull Request 歓迎！以下のガイドラインに従ってください：

1. **ブランチ**: `feature/機能名` または `fix/バグ名`
2. **コミット**: [Conventional Commits](https://www.conventionalcommits.org/)
3. **テスト**: 新機能には必ずテストを追加
4. **Lint**: `ruff check .` と `black .` を実行
5. **PR**: GitHub Copilot による自動レビューを確認

## ライセンス

MIT License - 詳細は [LICENSE](LICENSE) を参照

## 作者

[@YOUR_USERNAME](https://github.com/YOUR_USERNAME)

---

**面接アピールポイント** 🎯

- ✅ **モダンUI**: ダークテーマ + グラスモーフィズム + アニメーション
- ✅ **AI統合**: OpenAI API による自動要約・リスク評価
- ✅ **マルチソース**: Yahoo!/Nifty 両対応の横断検索
- ✅ **堅牢性**: 76テストケース、カバレッジ80%+
- ✅ **セキュリティ**: CSRF, XSS, SQLインジェクション対策完備
- ✅ **CI/CD**: GitHub Actions による完全自動化
- ✅ **スケーラビリティ**: Docker + Gunicorn + PostgreSQL
- ✅ **保守性**: 型ヒント、Docstring、詳細ドキュメント

**このプロジェクトは、実務レベルのモダンWeb開発スキルを網羅的に示す技術ポートフォリオです。**
