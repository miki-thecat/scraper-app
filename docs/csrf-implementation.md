# CSRF保護 実装解説

## 📋 実装完了日
2025-10-29

## 🎯 実装概要

Flask-WTFを使用してCSRF（Cross-Site Request Forgery）保護を実装しました。
これにより、外部サイトからの不正なフォーム送信を防ぎ、セキュリティを強化しています。

---

## 📁 変更ファイル一覧

### 1. 設定ファイル

#### `app/config.py`
```python
# CSRF Protection
WTF_CSRF_ENABLED = True          # CSRF保護を有効化
WTF_CSRF_TIME_LIMIT = 3600       # トークン有効期限（秒）= 1時間
WTF_CSRF_SSL_STRICT = False      # 開発環境ではHTTP許可
WTF_CSRF_CHECK_DEFAULT = True    # 全エンドポイントで検証
```

**本番環境（ProdConfig）**
```python
WTF_CSRF_SSL_STRICT = True  # 本番環境ではHTTPS必須
```

**解説:**
- `WTF_CSRF_ENABLED`: CSRF保護の有効/無効を切り替え
- `WTF_CSRF_TIME_LIMIT`: トークンの有効期限（秒単位）。1時間に設定
- `WTF_CSRF_SSL_STRICT`: HTTPS接続を強制するか。開発環境はFalse、本番はTrue
- `WTF_CSRF_CHECK_DEFAULT`: デフォルトで全POST/PUT/DELETEを保護

---

### 2. アプリケーション初期化

#### `app/__init__.py`

**インポート追加:**
```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
```

**初期化:**
```python
def create_app(config_class: type[Config] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    init_db(app)
    Migrate(app, db)
    csrf.init_app(app)  # ← CSRF保護を初期化
```

**解説:**
- `CSRFProtect()` でグローバルインスタンスを作成
- `csrf.init_app(app)` でアプリに適用
- これだけで全POST/PUT/PATCH/DELETEリクエストが自動保護される

---

**エラーハンドラ追加:**
```python
def _init_csrf_error_handler(app: Flask) -> None:
    """CSRFエラー時のカスタムハンドラを設定"""
    from flask_wtf.csrf import CSRFError
    from flask import render_template

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        app.logger.warning(f'CSRF validation failed: {e.description}')
        return render_template(
            'error.html',
            error='セキュリティ上の理由により、リクエストが拒否されました。',
            details=e.description
        ), 400
```

**解説:**
- CSRFエラー（400）が発生した際のカスタムハンドラ
- ユーザーフレンドリーな日本語エラーメッセージを表示
- エラー詳細をログに記録（セキュリティ監視用）

---

### 3. テンプレート修正

#### `app/templates/layout.html`

**meta タグ追加:**
```html
<head>
    <meta charset="utf-8">
    <title>{% block title %}スクレイピングアプリケーション{% endblock %}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">  <!-- 追加 -->
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
```

**解説:**
- JavaScript（Ajax/Fetch API）からCSRFトークンを取得できるようにmeta タグに埋め込み
- `{{ csrf_token() }}` はFlask-WTFが提供するヘルパー関数

**Ajax使用例:**
```javascript
fetch('/scrape', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
    },
    body: JSON.stringify({ url: 'https://...' })
});
```

---

**ログアウトフォーム:**
```html
<form method="post" action="{{ url_for('auth.logout') }}">
    {{ csrf_token() }}  <!-- 追加 -->
    <button class="button button--ghost button--compact" type="submit">ログアウト</button>
</form>
```

---

#### `app/templates/index.html`

**スクレイピングフォーム（メイン）:**
```html
<form class="scrape-form" method="post" action="{{ url_for('main.scrape') }}">
    {{ csrf_token() }}  <!-- 追加 -->
    <label for="url" class="sr-only">スクレイピングするURLを入力</label>
    <div class="scrape-form__field">
        <input id="url" name="url" type="url" placeholder="https://news.yahoo.co.jp/articles/..." required>
        <p class="scrape-form__note">Yahoo!ニュースの記事URLのみ対応しています</p>
    </div>
    <button class="button button--primary" type="submit">実行する</button>
</form>
```

**最新記事からのスクレイピングフォーム:**
```html
<form method="post" action="{{ url_for('main.scrape') }}">
    {{ csrf_token() }}  <!-- 追加 -->
    <input type="hidden" name="url" value="{{ item.url }}">
    <button class="button button--primary" type="submit">AI解析する</button>
</form>
```

---

#### `app/templates/login.html`

**ログインフォーム:**
```html
<form method="post" action="{{ url_for('auth.login_post') }}" class="auth-form">
    {{ csrf_token() }}  <!-- 追加 -->
    {% if next_url %}
    <input type="hidden" name="next" value="{{ next_url }}">
    {% endif %}
    <div class="auth-form__field">
        <label for="username">ユーザー名</label>
        <input id="username" name="username" type="text" autocomplete="username" required placeholder="admin">
    </div>
    <div class="auth-form__field">
        <label for="password">パスワード</label>
        <div class="auth-form__password">
            <input id="password" name="password" type="password" autocomplete="current-password" required placeholder="••••••••">
        </div>
    </div>
    <div class="auth-form__actions">
        <button class="button button--primary button--full" type="submit">ログイン</button>
    </div>
</form>
```

---

#### `app/templates/latest_feed.html`

**最新記事フィードのスクレイピングフォーム:**
```html
<form method="post" action="{{ url_for('main.scrape') }}">
    {{ csrf_token() }}  <!-- 追加 -->
    <input type="hidden" name="url" value="{{ item.url }}">
    <button class="button button--primary" type="submit">AI解析する</button>
</form>
```

---

#### `app/templates/result.html`

**AI推論再実行フォーム:**
```html
<form class="surface__actions" method="post" action="{{ url_for('main.rerun_ai', article_id=article.id) }}">
    {{ csrf_token() }}  <!-- 追加 -->
    <button class="button button--primary" type="submit">{% if inference %}AI推論を再実行{% else %}AI推論を実行{% endif %}</button>
</form>
```

---

### 4. テストファイル

#### `tests/test_csrf.py` (新規作成)

**テストケース:**

1. **test_scrape_without_csrf_token_returns_400**
   - CSRFトークンなし → 400エラー

2. **test_scrape_with_invalid_csrf_token_returns_400**
   - 間違ったトークン → 400エラー

3. **test_scrape_with_valid_csrf_token_succeeds**
   - 正しいトークン → 成功

4. **test_login_without_csrf_token_returns_400**
   - ログインフォームでもCSRF保護が有効

5. **test_login_with_valid_csrf_token_succeeds**
   - 正しいトークンでログイン成功

6. **test_logout_without_csrf_token_returns_400**
   - ログアウトでもCSRF保護が有効

7. **test_get_request_not_protected_by_csrf**
   - GETリクエストは保護対象外

8. **test_csrf_token_in_meta_tag**
   - meta タグにトークンが埋め込まれている

9. **test_csrf_error_handler_returns_custom_message**
   - カスタムエラーメッセージが返る

---

## 🔍 動作の仕組み

### フロー図

```
┌────────────────────────────────────────────────────────┐
│ 1. ユーザーがページにアクセス（GET）                      │
└────────────────────────────────────────────────────────┘
                          ↓
        サーバー: ランダムなトークンを生成
                  session['csrf_token'] = "a8f3d9e2..."
                          ↓
        HTMLに埋め込んで返す
        <input type="hidden" name="csrf_token" value="a8f3d9e2...">
                          ↓
┌────────────────────────────────────────────────────────┐
│ 2. ユーザーがフォーム送信（POST）                        │
└────────────────────────────────────────────────────────┘
                          ↓
        ブラウザ: フォームデータ + CSRFトークンを送信
                  POST /scrape
                  Cookie: session=xyz
                  Body: url=...&csrf_token=a8f3d9e2...
                          ↓
        サーバー: トークンを検証
                  session['csrf_token'] == form['csrf_token']?
                          ↓
                  ┌─────YES─────┐    ┌─────NO─────┐
                  │ 処理続行    │    │ 400エラー   │
                  └─────────────┘    └─────────────┘

┌────────────────────────────────────────────────────────┐
│ 3. 攻撃者が外部サイトから送信を試みる（evil.com）        │
└────────────────────────────────────────────────────────┘
                          ↓
        攻撃サイト: フォームを自動送信
                    POST /scrape
                    Cookie: session=xyz（被害者のCookie）
                    Body: url=...&csrf_token=??? （知らない！）
                          ↓
        サーバー: トークンが一致しない
                  → 400エラー（攻撃失敗）
```

---

## 🛡️ セキュリティのポイント

### 1. なぜ攻撃者はトークンを取得できないのか

**Same-Origin Policy（同一生成元ポリシー）**

ブラウザのセキュリティ機能により、他サイト（evil.com）から
あなたのサイト（your-app.com）のHTMLコンテンツを読み取ることはできません。

```javascript
// evil.com のJavaScript

// ❌ これは失敗する（ブラウザがブロック）
fetch('https://your-app.com/')
  .then(res => res.text())
  .then(html => {
    // HTMLを取得してトークンを抽出...
    // → Same-Origin Policyでブロックされる！
  });
```

### 2. トークンの保存場所

- **サーバー側**: セッション（Cookieまたはサーバーストレージ）
- **クライアント側**: フォームのhidden inputまたはmeta タグ

### 3. トークンの有効期限

- デフォルト: 3600秒（1時間）
- 設定: `WTF_CSRF_TIME_LIMIT`

---

## ✅ 実装チェックリスト

- [x] Flask-WTFのインストール確認（requirements.txt）
- [x] app/config.py に CSRF設定追加
- [x] app/__init__.py に csrf.init_app(app) 追加
- [x] CSRFエラーハンドラ追加
- [x] layout.html に meta タグ追加
- [x] 全フォームテンプレートに {{ csrf_token() }} 追加
  - [x] index.html（2箇所）
  - [x] login.html
  - [x] layout.html（ログアウト）
  - [x] latest_feed.html
  - [x] result.html
- [x] テスト作成（tests/test_csrf.py）

---

## 🧪 テスト実行方法

```bash
# CSRF関連のテストのみ実行
pytest tests/test_csrf.py -v

# 全テスト実行
pytest -v

# カバレッジ付き
pytest --cov=app --cov-report=term-missing
```

---

## 📊 期待される結果

### 正常系
- フォームからの送信: **成功**（200 or 302）
- CSRFトークン付きPOST: **成功**

### 異常系
- CSRFトークンなしPOST: **400エラー**
- 間違ったトークン: **400エラー**
- 期限切れトークン: **400エラー**
- 外部サイトからの送信: **400エラー**

---

## 💡 運用上の注意点

### 1. セッション管理
CSRFトークンはセッションに保存されるため、以下に注意：

- セッションタイムアウト設定を適切に（PERMANENT_SESSION_LIFETIME）
- セッションストレージの容量確保（Redis使用時）

### 2. 開発環境
開発環境では `WTF_CSRF_SSL_STRICT = False` にしてHTTP許可

### 3. 本番環境
本番環境では `WTF_CSRF_SSL_STRICT = True` でHTTPS必須

### 4. API エンドポイント
将来的にREST APIを公開する場合は、以下のように除外：

```python
from flask_wtf.csrf import csrf

@app.route('/api/articles', methods=['POST'])
@csrf.exempt  # API用に除外
def api_create_article():
    # JWT認証を使う
    pass
```

---

## 🔗 関連ドキュメント

- [Flask-WTF 公式ドキュメント](https://flask-wtf.readthedocs.io/)
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [CSRF保護完全ガイド](./csrf-protection-guide.md)

---

## 📝 変更履歴

| 日付 | 変更内容 |
|------|----------|
| 2025-10-29 | CSRF保護実装完了 |

---

**実装完了！セキュリティが大幅に向上しました。** 🎉
