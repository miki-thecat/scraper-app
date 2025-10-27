# AI Git操作ルール

このファイルは、AIアシスタントがGit操作を行う際のルールを定義します。

## 🎯 基本原則

### 1. コミットのタイミング

**必須コミット:**
- ✅ 機能実装完了時（テスト合格後）
- ✅ ファイル追加・削除時
- ✅ バグ修正完了時
- ✅ ドキュメント更新時

**禁止コミット:**
- ❌ テスト失敗中
- ❌ Lintエラーあり
- ❌ 作業途中（WIP）は `git stash` を使用

### 2. プッシュのタイミング

**自動プッシュ:**
- ✅ コミット直後（基本）
- ✅ PR準備完了時
- ✅ ドキュメント更新時

**プッシュ前確認:**
- ✅ テスト実行: `pytest`
- ✅ Lint実行: `ruff check .`
- ✅ コミットメッセージ確認

### 3. ブランチ管理

**ブランチ作成ルール:**
- 新機能: `feature/機能名`
- バグ修正: `fix/バグ名`
- その他: `chore/タスク名`

**マージルール:**
- `main`へは必ずPR経由
- 直接pushは禁止

---

## 📋 AIの作業フロー

### パターン1: 新機能開発

```
1. git checkout main
2. git pull origin main
3. git checkout -b feature/機能名
4. [実装作業]
5. ruff check .
6. pytest
7. git add <変更ファイル>
8. git commit -m "feat: 機能の説明"
9. git push origin feature/機能名
10. [PR作成を提案]
```

### パターン2: バグ修正

```
1. git checkout -b fix/バグ名
2. [修正作業]
3. pytest
4. git add <修正ファイル>
5. git commit -m "fix: バグの説明"
6. git push origin fix/バグ名
```

### パターン3: ドキュメント更新

```
1. [ドキュメント編集]
2. git add docs/
3. git commit -m "docs: 更新内容"
4. git push origin <現在のブランチ>
```

### パターン4: 作業中断

```
1. git stash save "WIP: 作業内容"
2. [中断理由を説明]
3. [再開方法を提示]
```

---

## 🔄 コミットメッセージフォーマット

### 必須フォーマット

```
<type>: <subject>

<body>（詳細説明）
```

### Type（種類）

- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント
- `style`: コードフォーマット
- `refactor`: リファクタリング
- `test`: テスト追加・修正
- `chore`: ビルド、設定変更
- `perf`: パフォーマンス改善

### Subject（件名）

- 50文字以内
- 命令形で記述（「追加する」ではなく「追加」）
- 日本語OK

### Body（本文）

- 72文字で改行
- 変更理由、影響範囲を記載
- 箇条書きOK

---

## ✅ チェックリスト

### コミット前

- [ ] テスト実行済み（`pytest`）
- [ ] Lint通過済み（`ruff check .`）
- [ ] 変更内容を確認（`git diff`）
- [ ] コミットメッセージ作成
- [ ] 不要なファイルを除外

### プッシュ前

- [ ] コミット内容を確認（`git log -1`）
- [ ] ブランチ名を確認（`git branch --show-current`）
- [ ] リモート状態を確認（`git fetch`）
- [ ] コンフリクトがないか確認

### PR作成前

- [ ] 全テスト合格
- [ ] Lintエラー0
- [ ] ドキュメント更新済み
- [ ] コミット履歴がクリーン

---

## 🚨 緊急時の対応

### テスト失敗時

```bash
# コミットしない
# 修正してから再度テスト
pytest
# 合格後にコミット
```

### Lintエラー時

```bash
# 自動修正を試みる
ruff check . --fix
# 手動修正が必要な場合は修正
# 合格後にコミット
```

### コンフリクト発生時

```bash
# ユーザーに報告
# 自動解決は試みない
# 手動解決を依頼
```

---

## 🎯 実装例

### 良い例

```bash
# 機能完成 → テスト → Lint → コミット → プッシュ
pytest
ruff check .
git add app/logging_config.py app/config.py app/__init__.py
git commit -m "feat: ロギング機能を追加

- 構造化ログ（JSON形式対応）
- リクエストID追跡
- エラー詳細記録"
git push origin feature/logging-enhancement
```

### 悪い例

```bash
# テスト前にコミット（NG）
git add .
git commit -m "WIP"
git push
```

---

## 📊 進捗報告

### コミット後

```
✅ コミット完了: feat: ロギング機能を追加
📦 変更ファイル: 3件
🔗 ブランチ: feature/logging-enhancement
```

### プッシュ後

```
✅ プッシュ完了: origin/feature/logging-enhancement
🔗 PR作成URL: https://github.com/user/repo/compare/feature/logging-enhancement
```

---

## 💡 ベストプラクティス

### 1. 小さく頻繁にコミット

```bash
# Good: 1機能1コミット
git commit -m "feat: ログフォーマッター追加"
git commit -m "test: ログフォーマッターのテスト追加"
git commit -m "docs: ログ設定を文書化"

# Bad: 大きな1コミット
git commit -m "ログ機能実装"  # 10ファイル変更
```

### 2. 意味のあるメッセージ

```bash
# Good
git commit -m "fix: OpenAI APIタイムアウトを30秒に延長"

# Bad
git commit -m "修正"
git commit -m "update"
```

### 3. テスト・Lintは必須

```bash
# 必ず実行
pytest && ruff check . && git commit -m "..."
```

---

## 🔧 設定済み項目

以下の設定が適用されています：

- `pull.rebase = false` - マージを使用
- `core.autocrlf = input` - 改行コード統一
- コミットテンプレート: `.git-commit-template`

---

**このルールに従うことで、クリーンなGit履歴を維持します。**
