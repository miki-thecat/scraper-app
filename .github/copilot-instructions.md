# GitHub Copilot Instructions

## プロジェクト概要
Yahoo!ニュース・@niftyニュースの記事スクレイピング + AI要約/リスク評価Webアプリ

## 技術スタック
- **Backend**: Python 3.11, Flask, SQLAlchemy
- **Frontend**: Jinja2, CSS (モダンなグラデーション設計)
- **Database**: PostgreSQL (production), SQLite (dev)
- **AI**: OpenAI API (GPT-4)
- **Testing**: pytest, coverage
- **CI/CD**: GitHub Actions

## コーディング規約

### Python
- PEP 8準拠
- Type hints必須 (`from __future__ import annotations` 使用)
- Docstring: Google Style
- Linter: Ruff, Black, isort
- 行の長さ: 120文字まで

### 命名規則
- 関数/変数: `snake_case`
- クラス: `PascalCase`
- 定数: `UPPER_SNAKE_CASE`
- プライベート: `_leading_underscore`

### Import順序
```python
# 1. 標準ライブラリ
from __future__ import annotations
import os
from datetime import datetime

# 2. サードパーティ
from flask import Flask, request
import requests

# 3. ローカル
from app.models import Article
from app.services import scraping
```

### エラーハンドリング
- 必ず適切な例外を捕捉
- ログ出力必須
- ユーザーフレンドリーなエラーメッセージ

```python
try:
    result = risky_operation()
except SpecificError as exc:
    logger.error("Operation failed", exc_info=exc)
    raise ServiceError("わかりやすいエラーメッセージ") from exc
```

## アーキテクチャ

### ディレクトリ構造
```
app/
├── services/       # ビジネスロジック
│   ├── scraping.py    # スクレイピング
│   ├── parsing.py     # HTML解析
│   ├── nifty_news.py  # @niftyニュース専用
│   ├── articles.py    # 記事管理
│   └── ai.py          # AI推論
├── models/         # データモデル
├── routes.py       # ルーティング
└── templates/      # Jinja2テンプレート
```

### データフロー
```
URL入力 → scraping.fetch()
       → parsing.parse_article() or nifty_news.NiftyNewsParser.parse_article()
       → articles.ingest_article()
       → ai.run_inference()
       → DB保存
```

## 対応ニュースサイト

### Yahoo!ニュース
- URL: `https://news.yahoo.co.jp/articles/[ID]`
- パーサー: `parsing.parse_article()`
- 特徴: JSON-LD + Open Graph

### @niftyニュース
- URL: 
  - `https://news.nifty.com/topics/[publisher]/[ID]/` (自動的に記事URLへ)
  - `https://news.nifty.com/article/[category]/[subcategory]/[ID]/`
- パーサー: `nifty_news.NiftyNewsParser.parse_article()`
- 特徴: Next.js, JSON-LD, article_body_text

## テスト方針

### 必須カバレッジ
- 全体: 80%以上
- サービス層: 90%以上
- クリティカルパス: 100%

### テストファイル命名
- `test_[module_name].py`
- `Test[ClassName]`クラス
- `test_[function_name]_[scenario]`関数

### モック使用
```python
@pytest.fixture
def mock_openai(mocker):
    return mocker.patch('app.services.ai.openai.ChatCompletion.create')
```

## AI推論

### リスクレベル
- **MINIMAL** (0-2.9): 安全
- **LOW** (3.0-4.9): 低リスク
- **MODERATE** (5.0-6.9): 中リスク
- **HIGH** (7.0-8.9): 高リスク
- **CRITICAL** (9.0-10.0): 緊急

### プロンプト設計
- 簡潔な要約（150字以内）
- リスクスコア（0-10）
- 具体的な根拠

## セキュリティ

### 必須対策
- CSRF保護（全フォーム）
- SQLインジェクション対策（SQLAlchemy）
- XSS対策（Jinja2自動エスケープ）
- セキュリティヘッダー（CSP, X-Frame-Options等）

### 認証
- セッションベース
- セキュアなCookie設定
- パスワードハッシュ（pbkdf2_sha256）

## パフォーマンス

### DB最適化
- インデックス: url, created_at, published_at
- ページネーション必須
- N+1問題回避

### キャッシュ
- 記事は重複チェック（URL）
- AI推論結果は永続化

## デプロイ

### 環境変数
```bash
FLASK_ENV=production
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...
SECRET_KEY=[random-string]
```

### GitHub Actions
- プッシュ → テスト自動実行
- mainマージ → 自動デプロイ
- PRには自動レビュー

## コミットメッセージ

### Conventional Commits
```
feat: 新機能追加
fix: バグ修正
docs: ドキュメント更新
style: フォーマット変更
refactor: リファクタリング
test: テスト追加
chore: その他の変更
```

### 例
```
feat: Add @nifty News integration

- Implement NiftyNewsParser
- Support both topics and article URLs
- Add JSON-LD extraction
- Update UI to show multi-source support

Closes #123
```

## Copilotへの期待

### コード生成時
- Type hints付き関数を生成
- 適切なエラーハンドリング
- ログ出力を含める
- Docstringを必ず記載

### レビュー時
- セキュリティ脆弱性チェック
- パフォーマンス問題指摘
- テストカバレッジ確認
- コーディング規約準拠確認

### 提案時
- 具体的な修正案
- コード例を含める
- 理由を明確に説明

## よくあるパターン

### 記事取得
```python
def ingest_article(url: str) -> ArticleIngestionResult:
    """記事を取得してDBに保存"""
    # 1. URL検証
    if not scraping.is_allowed(url):
        raise ArticleIngestionError("対応していないURL")
    
    # 2. 既存チェック
    existing = db.session.query(Article).filter_by(url=url).first()
    if existing:
        return ArticleIngestionResult(article=existing, status="existing")
    
    # 3. スクレイピング
    response = scraping.fetch(url)
    
    # 4. パース（ソース判定）
    source = "nifty_news" if "nifty.com" in url else "yahoo"
    if source == "nifty_news":
        parsed = nifty_news.NiftyNewsParser.parse_article(response.text, url)
    else:
        parsed = parsing.parse_article(url, response.text)
    
    # 5. DB保存
    article = Article(url=parsed.url, title=parsed.title, ...)
    db.session.add(article)
    db.session.commit()
    
    # 6. AI推論（非同期）
    try:
        inference = ai.run_inference(article)
    except AIError as exc:
        logger.warning("AI inference failed", exc_info=exc)
    
    return ArticleIngestionResult(article=article, status="created")
```

## 優先順位

1. **セキュリティ**: 常に最優先
2. **テスト**: 機能追加前にテストを書く
3. **パフォーマンス**: N+1問題、大量データ対応
4. **UX**: わかりやすいエラーメッセージ
5. **ドキュメント**: コードは自己文書化

## 禁止事項

❌ ハードコードされた認証情報
❌ SQLの直書き
❌ グローバル変数の乱用
❌ 例外の握りつぶし（`except: pass`）
❌ テストなしでの機能追加

## 推奨事項

✅ 小さなコミット
✅ 単一責任の原則
✅ DRY（Don't Repeat Yourself）
✅ 明確な関数名
✅ 早期リターン（ネスト削減）

---

**このプロジェクトの目標**: ニフティ面接での技術力アピール
**期待される成果**: モダンで堅牢なスクレイピング + AI評価システム
