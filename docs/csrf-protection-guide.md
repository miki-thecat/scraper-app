# CSRF（Cross-Site Request Forgery）保護 完全解説

## 📚 目次
1. CSRF攻撃とは何か（基礎）
2. 実際の攻撃シナリオ（具体例）
3. なぜ危険なのか
4. CSRF保護の仕組み（詳細）
5. Flask-WTFによる実装（ステップバイステップ）
6. テスト方法
7. よくある質問（FAQ）

---

## 1️⃣ CSRF攻撃とは何か（基礎）

### Web の基本動作を理解する

#### 通常のログインフロー
```
1. ユーザー → https://your-app.com/login
   POST: username=alice&password=secret

2. サーバー → Cookieを発行
   Set-Cookie: session=abc123xyz; HttpOnly; Secure

3. ユーザー → 以降のリクエストで自動的にCookieが送信される
   Cookie: session=abc123xyz
```

#### ブラウザの重要な仕様
**「ブラウザは、どのサイトからのリクエストでもCookieを自動送信する」**

```
例：
- あなたのサイト（your-app.com）にログイン中
- 悪意のサイト（evil.com）を訪問
- evil.comから your-app.com へのリクエストを送ると...
  → ブラウザは自動的に your-app.com のCookieを送信してしまう！
```

---

## 2️⃣ 実際の攻撃シナリオ（具体例）

### シナリオ1: 銀行サイトへの不正送金

#### 攻撃前の状態
```
あなた（被害者）:
- A銀行のサイトにログイン中
- 残高: 100万円
```

#### 攻撃の流れ

**Step 1: 攻撃者が罠サイトを用意**
```html
<!-- http://evil.com/free-gift.html -->
<!DOCTYPE html>
<html>
<head>
    <title>無料プレゼント！</title>
</head>
<body>
    <h1>おめでとうございます！商品が当選しました</h1>
    <p>受け取るには下のボタンをクリック</p>
    
    <!-- 見えないフォーム（display:none） -->
    <form id="attack" action="https://bank-a.com/transfer" method="POST" style="display:none">
        <input name="to_account" value="攻撃者の口座番号">
        <input name="amount" value="1000000">
    </form>
    
    <script>
        // ページ読み込み時に自動送信
        document.getElementById('attack').submit();
    </script>
</body>
</html>
```

**Step 2: 被害者がリンクをクリック**
```
メール: 「無料プレゼント当選！ http://evil.com/free-gift.html」
↓
被害者がクリック
↓
evil.com のページが開く
↓
JavaScript が自動的にフォームを送信
```

**Step 3: ブラウザの挙動**
```
ブラウザ:
「https://bank-a.com/transfer へPOSTリクエストを送信します」
「お、bank-a.com へのリクエストだな。Cookieを自動で付けよう」

送信内容:
POST https://bank-a.com/transfer
Cookie: session=被害者のセッションID  ← 自動で付く！
Content-Type: application/x-www-form-urlencoded

to_account=攻撃者の口座番号&amount=1000000
```

**Step 4: 銀行サーバーの処理**
```
銀行サーバー:
「セッションIDを確認...OK、ログイン中だ」
「送金処理を実行します」
「被害者の口座 → 攻撃者の口座へ 100万円送金」
```

**結果: 被害者は何も気づかずに100万円失う** 😱

---

### シナリオ2: あなたのスクレイピングアプリでの攻撃

#### 現在の実装（CSRF保護なし）

```python
# app/routes.py
@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form.get('url')
    # URLをスクレイプして保存
    article = scrape_and_save(url)
    return redirect(f'/result/{article.id}')
```

#### 攻撃シナリオ

**攻撃者の目的:**
- あなたのサーバーに負荷をかける（DoS攻撃）
- 悪意のあるURLをスクレイプさせる
- データベースを汚染する

**攻撃コード（evil.com）:**
```html
<!DOCTYPE html>
<html>
<body>
    <h1>面白い動画！</h1>
    <video src="fake.mp4"></video>
    
    <!-- 裏で1秒ごとにスクレイピングリクエストを送信 -->
    <script>
        setInterval(() => {
            const form = document.createElement('form');
            form.action = 'https://your-app.com/scrape';
            form.method = 'POST';
            form.target = '_blank'; // 別ウィンドウで開く（気づかれない）
            
            const input = document.createElement('input');
            input.name = 'url';
            input.value = 'https://malicious-site.com/attack';
            
            form.appendChild(input);
            document.body.appendChild(form);
            form.submit();
            form.remove();
        }, 1000); // 1秒ごと
    </script>
</body>
</html>
```

**被害:**
```
- 1秒ごとにスクレイピングが実行される
- OpenAI APIが呼ばれる → 課金が発生
- データベースが不正なデータで埋まる
- サーバー負荷が高まる
```

---

## 3️⃣ なぜ危険なのか

### 危険性のポイント

| 項目 | 説明 |
|------|------|
| **本人確認ができない** | Cookieだけでは「本当にユーザーが操作したか」判別不可 |
| **自動化可能** | スクリプトで大量攻撃できる |
| **気づきにくい** | バックグラウンドで実行されるため被害者は気づかない |
| **影響範囲が広い** | POST/PUT/DELETEすべてが対象 |

### このプロジェクトでの具体的リスク

```
1. スクレイピングの乱用
   → OpenAI API料金が爆発的に増加（1リクエスト約10円として）
   → 攻撃者が1時間で3600リクエスト = 36,000円

2. データベース汚染
   → 悪意のあるURLが大量保存
   → ストレージコスト増加

3. サーバーリソース枯渇
   → 正規ユーザーがアクセスできなくなる
```

---

## 4️⃣ CSRF保護の仕組み（詳細）

### 基本原理: ワンタイムトークン

**「サーバーが発行した秘密の合言葉を確認する」**

#### フロー図解

```
┌─────────────────────────────────────────────────────────┐
│ Step 1: フォーム表示リクエスト                            │
└─────────────────────────────────────────────────────────┘

ユーザー → サーバー
GET /

サーバー:
1. ランダムなトークンを生成
   token = "a8f3d9e2b1c4..."
   
2. セッションに保存
   session['csrf_token'] = "a8f3d9e2b1c4..."
   
3. HTMLに埋め込んで返す
   <input type="hidden" name="csrf_token" value="a8f3d9e2b1c4...">

┌─────────────────────────────────────────────────────────┐
│ Step 2: フォーム送信                                      │
└─────────────────────────────────────────────────────────┘

ユーザー → サーバー
POST /scrape
Cookie: session=xyz
Body: url=...&csrf_token=a8f3d9e2b1c4...

サーバー:
1. Cookieからセッション取得
   session['csrf_token'] = "a8f3d9e2b1c4..."
   
2. フォームから送られたトークンと比較
   form['csrf_token'] = "a8f3d9e2b1c4..."
   
3. 一致？
   YES → 処理続行
   NO  → 400 Bad Request

┌─────────────────────────────────────────────────────────┐
│ 攻撃時の挙動                                              │
└─────────────────────────────────────────────────────────┘

攻撃者（evil.com） → あなたのサーバー
POST /scrape
Cookie: session=xyz （被害者のCookie）
Body: url=...&csrf_token=??? （攻撃者は知らない！）

サーバー:
1. session['csrf_token'] = "a8f3d9e2b1c4..."
2. form['csrf_token'] = ??? （空 or 間違った値）
3. 不一致！ → 400 Bad Request （攻撃失敗）
```

### なぜ攻撃者はトークンを取得できないのか

#### Same-Origin Policy（同一生成元ポリシー）

```javascript
// evil.com のJavaScript

// ❌ これはできない（Same-Origin Policyで禁止）
fetch('https://your-app.com/')
  .then(res => res.text())
  .then(html => {
    // HTMLを取得してトークンを抽出...
    // → ブラウザがブロック！
  });

// ❌ これもできない
const iframe = document.createElement('iframe');
iframe.src = 'https://your-app.com/';
document.body.appendChild(iframe);
const token = iframe.contentDocument.querySelector('[name=csrf_token]').value;
// → ブラウザがブロック！
```

**ブラウザのセキュリティ機能により、他サイトのコンテンツは読み取れない**

---

## 5️⃣ Flask-WTFによる実装（ステップバイステップ）

### ステップ1: パッケージ確認

```bash
# requirements.txt に既にあるか確認
grep Flask-WTF requirements.txt
```

### ステップ2: アプリケーション初期化

```python
# app/__init__.py
from flask import Flask
from flask_wtf.csrf import CSRFProtect

# グローバルインスタンス
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    
    # 設定読み込み
    app.config.from_object('config.Config')
    
    # CSRF保護を有効化
    csrf.init_app(app)
    # ↑ これだけで全POST/PUT/PATCH/DELETEが自動保護される
    
    # ルート登録
    from app import routes
    app.register_blueprint(routes.bp)
    
    return app
```

### ステップ3: 設定ファイル

```python
# config.py
import os

class Config:
    # 必須: SECRET_KEYがないとトークン生成できない
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # CSRF設定
    WTF_CSRF_ENABLED = True  # CSRF保護を有効化
    WTF_CSRF_TIME_LIMIT = 3600  # トークン有効期限（秒）= 1時間
    WTF_CSRF_SSL_STRICT = True  # HTTPS必須（本番環境）
    WTF_CSRF_CHECK_DEFAULT = True  # デフォルトで全エンドポイント検証
    
    # CSRF除外パス（正規表現）
    WTF_CSRF_EXEMPT_LIST = [
        r'/api/.*',  # /api/* は全て除外（JWT認証を使うため）
    ]
```

### ステップ4: テンプレート修正

#### Before（CSRF保護なし）
```html
<!-- templates/index.html -->
<form method="POST" action="/scrape">
    <input type="text" name="url" placeholder="記事URL" required>
    <button type="submit">スクレイプ</button>
</form>
```

#### After（CSRF保護あり）
```html
<!-- templates/index.html -->
<form method="POST" action="/scrape">
    <!-- この1行を追加するだけ -->
    {{ csrf_token() }}
    
    <input type="text" name="url" placeholder="記事URL" required>
    <button type="submit">スクレイプ</button>
</form>
```

#### 生成されるHTML
```html
<form method="POST" action="/scrape">
    <!-- Flask-WTFが自動生成 -->
    <input type="hidden" name="csrf_token" value="IjA4ZjNkOWUyYjFjNC4uLiI.ZyHx5w.XYZ...">
    
    <input type="text" name="url" placeholder="記事URL" required>
    <button type="submit">スクレイプ</button>
</form>
```

### ステップ5: Ajax対応（必要な場合）

```html
<!-- templates/index.html -->
<script>
// CSRFトークンをmetaタグに埋め込む
<meta name="csrf-token" content="{{ csrf_token() }}">

// Fetch APIで送信
fetch('/scrape', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
    },
    body: JSON.stringify({ url: 'https://...' })
});
</script>
```

### ステップ6: API除外設定

```python
# app/routes.py
from flask_wtf.csrf import csrf

# 方法1: デコレーターで除外
@app.route('/api/articles', methods=['POST'])
@csrf.exempt
def api_create_article():
    # JWT認証を使うのでCSRF不要
    pass

# 方法2: Blueprintごと除外
api_bp = Blueprint('api', __name__, url_prefix='/api')
csrf.exempt(api_bp)
```

### ステップ7: エラーハンドリング

```python
# app/__init__.py
from flask_wtf.csrf import CSRFError

def create_app():
    app = Flask(__name__)
    csrf.init_app(app)
    
    # CSRFエラー時のカスタムハンドラ
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        app.logger.warning(f'CSRF validation failed: {e.description}')
        return render_template('csrf_error.html', reason=e.description), 400
    
    return app
```

```html
<!-- templates/csrf_error.html -->
<!DOCTYPE html>
<html>
<head>
    <title>セキュリティエラー</title>
</head>
<body>
    <h1>リクエストを処理できませんでした</h1>
    <p>セキュリティ上の理由により、このリクエストは拒否されました。</p>
    <p>理由: {{ reason }}</p>
    <p><a href="{{ url_for('index') }}">ホームに戻る</a></p>
</body>
</html>
```

---

## 6️⃣ テスト方法

### テストケース1: 正常系（トークンあり）

```python
# tests/test_csrf.py
import pytest
from flask import session

def test_scrape_with_valid_csrf_token(client, app):
    """正しいCSRFトークンがあれば成功"""
    with client:
        # Step 1: フォームページを取得（トークン生成）
        response = client.get('/')
        assert response.status_code == 200
        
        # セッションからトークン取得
        with client.session_transaction() as sess:
            csrf_token = sess.get('csrf_token')
        
        assert csrf_token is not None
        
        # Step 2: トークン付きでPOST
        response = client.post('/scrape', data={
            'url': 'https://news.yahoo.co.jp/articles/test',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
```

### テストケース2: 異常系（トークンなし）

```python
def test_scrape_without_csrf_token(client):
    """CSRFトークンがないと400エラー"""
    response = client.post('/scrape', data={
        'url': 'https://news.yahoo.co.jp/articles/test'
        # csrf_token なし
    })
    
    assert response.status_code == 400
    assert b'CSRF' in response.data or b'csrf' in response.data
```

### テストケース3: 異常系（間違ったトークン）

```python
def test_scrape_with_invalid_csrf_token(client):
    """間違ったCSRFトークンだと400エラー"""
    response = client.post('/scrape', data={
        'url': 'https://news.yahoo.co.jp/articles/test',
        'csrf_token': 'invalid-token-12345'
    })
    
    assert response.status_code == 400
```

### テストケース4: API除外確認

```python
def test_api_endpoint_exempt_from_csrf(client):
    """APIエンドポイントはCSRF不要"""
    response = client.post('/api/articles', 
        json={'url': 'https://news.yahoo.co.jp/articles/test'},
        headers={'Authorization': 'Bearer valid-jwt-token'}
    )
    
    # CSRFエラーにならない（JWT認証は別途必要）
    assert response.status_code != 400  # CSRF関連エラーではない
```

---

## 7️⃣ よくある質問（FAQ）

### Q1: GETリクエストもCSRF保護が必要？

**A: 不要です。GETは「読み取り専用」であるべきで、副作用を持たないため。**

```python
# ❌ 悪い例: GETで副作用
@app.route('/delete/<id>', methods=['GET'])
def delete_article(id):
    Article.query.filter_by(id=id).delete()
    # → CSRF攻撃可能！

# ✅ 良い例: DELETEまたはPOSTを使う
@app.route('/delete/<id>', methods=['DELETE', 'POST'])
def delete_article(id):
    Article.query.filter_by(id=id).delete()
    # → CSRF保護が効く
```

### Q2: APIとWebフォーム、どっちも保護できる？

**A: 使い分けが必要です。**

```
- Webフォーム（ブラウザ） → CSRF保護
- REST API（機械→機械） → JWT/API Key認証

設定:
- フォームエンドポイント: CSRF有効
- APIエンドポイント: CSRF無効 + JWT必須
```

### Q3: トークンの有効期限は？

**A: `WTF_CSRF_TIME_LIMIT`で設定可能（デフォルト3600秒=1時間）**

```python
# 長時間のフォーム入力を想定
WTF_CSRF_TIME_LIMIT = 7200  # 2時間

# 無期限（非推奨）
WTF_CSRF_TIME_LIMIT = None
```

### Q4: トークンはどこに保存される？

**A: サーバー側セッション（Cookieまたはサーバーストレージ）**

```
1. Flask-Session使用時
   → Redisやデータベースに保存

2. デフォルト（署名付きCookie）
   → ブラウザのCookieに暗号化保存
   → SECRET_KEYで署名・検証
```

### Q5: HTTPSじゃないとダメ？

**A: 本番環境では必須。開発環境ではHTTPでもOK。**

```python
class DevelopmentConfig(Config):
    WTF_CSRF_SSL_STRICT = False  # HTTP許可

class ProductionConfig(Config):
    WTF_CSRF_SSL_STRICT = True   # HTTPS必須
```

### Q6: 他のフレームワークでも同じ？

**A: 仕組みは同じですが、実装方法が異なります。**

```
Django → @csrf_protect デコレーター + {% csrf_token %}
Rails  → authenticity_token ヘルパー
Express.js → csurf ミドルウェア
```

---

## 📊 まとめ表

| 項目 | 内容 |
|------|------|
| **CSRF攻撃とは** | 外部サイトから不正なリクエストを送信する攻撃 |
| **なぜ成功するか** | ブラウザが自動的にCookieを送信するため |
| **防御方法** | サーバー発行のワンタイムトークンで検証 |
| **Flaskでの実装** | Flask-WTF（3ステップで完了） |
| **保護対象** | POST/PUT/PATCH/DELETE |
| **除外対象** | GET + API（JWT認証使用） |
| **セキュリティレベル** | 高（Same-Origin Policyで保護） |

---

## 🎯 次のステップ

1. ✅ CSRF保護の理解（この資料）
2. ⏳ 実装（app/__init__.py, config.py, templates/*.html）
3. ⏳ テスト作成・実行
4. ⏳ ドキュメント更新（README.md）

**実装を始めますか？**
