# CI/CD パイプライン ドキュメント

## 概要

GitHub Actionsを活用した包括的なCI/CDパイプラインを実装。テスト、リント、セキュリティスキャン、ビルド、デプロイを自動化しています。

## ワークフロー構成

### 1. CI/CD Pipeline (`ci-cd.yml`)

#### トリガー条件

```yaml
on:
  push:
    branches: [main, develop, ai_api, feature/**]
  pull_request:
    branches: [main, develop]
  workflow_dispatch:  # 手動トリガー
```

#### ジョブ構成

##### a) Test Job

**目的**: アプリケーションの全テストを実行

**マトリックスビルド**:
- Python 3.11, 3.12 で並列テスト

**ステップ**:
1. PostgreSQL サービス起動（テスト用DB）
2. Python環境セットアップ + pip キャッシュ
3. 依存関係インストール
4. pytest 実行
5. カバレッジ計測（80%閾値チェック）
6. Codecov へアップロード
7. HTML レポート生成・保存

**環境変数**:
```yaml
DATABASE_URL: postgresql+psycopg2://test:test@localhost:5432/test_db
SECRET_KEY: test-secret-key-${{ github.sha }}
FLASK_ENV: testing
```

##### b) Lint Job

**目的**: コード品質チェック

**ツール**:
- **Ruff**: 高速Pythonリンター
- **Black**: コードフォーマッター
- **isort**: インポート順序チェック
- **mypy**: 型チェック（optional）
- **Bandit**: セキュリティ脆弱性検出
- **Safety**: 依存関係の既知脆弱性チェック

**特徴**:
- `continue-on-error: true` でビルドブロックしない
- GitHub Annotations でコード行に直接コメント

##### c) Security Job

**目的**: セキュリティスキャン

**ツール**:
- **Trivy**: ファイルシステムスキャン
- **CodeQL**: コード解析（別途設定可能）

**SARIF アップロード**:
- GitHub Security タブに結果を統合表示

##### d) Build Job

**目的**: Docker イメージのビルド・プッシュ

**プラットフォーム**:
- `linux/amd64`
- `linux/arm64` （Apple Silicon対応）

**タグ戦略**:
```yaml
type=ref,event=branch         # ブランチ名
type=sha,prefix={{branch}}-   # コミットSHA
type=raw,value=latest         # mainブランチのみ
```

**最適化**:
- GitHub Actions Cache (GHA) 使用
- マルチステージビルド
- レイヤーキャッシング

**イメージスキャン**:
- ビルド後にTrivyで脆弱性スキャン

##### e) Deploy Job

**目的**: 本番環境へデプロイ

**条件**:
```yaml
if: github.ref == 'refs/heads/main' && github.event_name == 'push'
```

**デプロイ先例**:
- AWS ECS
- EC2 + Docker Compose
- Kubernetes
- Google Cloud Run

**ヘルスチェック**:
- デプロイ後に `/health` エンドポイント確認

##### f) Performance Job

**目的**: 負荷テスト（オプション）

**ツール**:
- k6 または Apache Bench

---

### 2. Code Review (`code-review.yml`)

#### トリガー条件

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
  pull_request_review_comment:
    types: [created]
```

#### ジョブ構成

##### a) Copilot Review Job

**目的**: GitHub Copilot による AI コードレビュー

**機能**:
- コード品質分析
- セキュリティ脆弱性検出
- パフォーマンス最適化提案
- Python/Flask ベストプラクティス確認

**実装**:
```yaml
- uses: github/copilot-cli-action@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    pull-request: ${{ github.event.pull_request.number }}
```

##### b) Code Quality Job

**詳細なコード解析**:

| ツール | 目的 | 出力形式 |
|--------|------|----------|
| Ruff | リント | JSON |
| Black | フォーマット | テキスト |
| isort | インポート | テキスト |
| Pylint | 詳細解析 | JSON |
| Radon | 複雑度 | テキスト |
| Vulture | デッドコード | テキスト |
| Bandit | セキュリティ | JSON |
| Safety | 脆弱性 | JSON |

**レポート生成**:
- PRコメントに総合レポートを投稿
- 各ツールの結果を表形式で表示
- 重要度に応じた絵文字アイコン

**チェック作成**:
```javascript
await github.rest.checks.create({
  name: 'Code Quality Check',
  conclusion: 'success' | 'neutral' | 'failure',
  output: { title, summary, text }
});
```

##### c) Coverage Check Job

**カバレッジ解析**:
- pytest-cov でカバレッジ計測
- JSON/HTML レポート生成
- 80% 閾値チェック

**PRコメント**:
```markdown
## ✅ Test Coverage Report

**Overall Coverage:** 85.32%
**Lines Covered:** 1234 / 1447

| Metric | Value |
|--------|-------|
| Covered | 1234 |
| Missing | 213 |
...
```

---

## Secrets 設定

### 必須

```bash
GITHUB_TOKEN  # 自動提供（Actions デフォルト）
```

### オプション

```bash
CODECOV_TOKEN     # Codecov連携
EC2_SSH_KEY       # EC2デプロイ用
EC2_HOST          # EC2ホスト名
AWS_ACCESS_KEY_ID # AWS認証
AWS_SECRET_ACCESS_KEY
```

---

## ベストプラクティス

### 1. Concurrency 制御

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

同一ブランチの古いワークフローを自動キャンセル

### 2. Timeout 設定

```yaml
timeout-minutes: 15
```

無限ループ防止

### 3. Conditional Steps

```yaml
if: matrix.python-version == '3.11'
```

特定条件でのみ実行

### 4. Artifact 保存

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: coverage-report
    retention-days: 30
```

テスト結果・レポートを保存

### 5. Cache 活用

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```

依存関係キャッシュで高速化

---

## トラブルシューティング

### テスト失敗時

1. ログを確認: `Actions` タブ → 該当ワークフロー
2. ローカル再現:
   ```bash
   DATABASE_URL=... pytest -v
   ```
3. カバレッジ確認:
   ```bash
   pytest --cov=app --cov-report=html
   open htmlcov/index.html
   ```

### ビルド失敗時

1. Dockerfile 構文チェック
2. ローカルビルド:
   ```bash
   docker build -t test .
   docker run --rm test pytest
   ```

### デプロイ失敗時

1. Secrets 確認
2. 権限チェック
3. ヘルスエンドポイント確認

---

## パフォーマンス指標

### 目標時間

| ジョブ | 目標 | 実績 |
|--------|------|------|
| Test | 5分 | 3-4分 |
| Lint | 3分 | 2分 |
| Build | 10分 | 7-8分 |
| Deploy | 5分 | 3-5分 |

### コスト削減

- キャッシュ活用: ビルド時間 50% 削減
- マトリックス最小化: 必要なバージョンのみ
- Concurrency: 無駄なビルド削減

---

## 拡張予定

- [ ] E2Eテスト（Playwright/Cypress）
- [ ] Visual Regression Testing
- [ ] Database Migration Check
- [ ] API Contract Testing
- [ ] Slack/Discord 通知
- [ ] Rollback 機能
- [ ] Blue-Green Deployment
