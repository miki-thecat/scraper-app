# UI Design Documentation

## 概要

モダンでダークテーマベースのグラスモーフィズムUIを採用した、秀逸なユーザーインターフェースを実装しています。

## デザインコンセプト

### カラーパレット

```css
--color-page-bg: #0a0e27       /* ディープネイビー背景 */
--color-accent: #8b5cf6        /* パープルアクセント */
--color-secondary: #06b6d4     /* シアンセカンダリ */
```

### グラデーション

- **Primary Gradient**: `#8b5cf6 → #6366f1 → #06b6d4`
- **Accent Gradient**: Purple to Indigo with opacity
- **Glow Effect**: Radial gradient for depth

## 主要コンポーネント

### 1. グラスモーフィズム

```css
background: rgba(255, 255, 255, 0.03);
backdrop-filter: blur(20px) saturate(180%);
border: 1px solid rgba(139, 92, 246, 0.2);
```

**特徴:**
- 半透明背景で奥行き感を演出
- ブラーエフェクトでモダンな質感
- グローボーダーで視認性向上

### 2. アニメーション

#### Float Animation (背景グロー)
```css
@keyframes float {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(30px, -30px) scale(1.1); }
    66% { transform: translate(-20px, 20px) scale(0.9); }
}
```

#### Shimmer Effect (スコアバッジ)
```css
@keyframes shimmer {
    0%, 100% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
    50% { transform: translateX(100%) translateY(100%) rotate(45deg); }
}
```

### 3. インタラクティブ要素

#### ボタンホバー
- `translateY(-2px)`: 浮き上がり効果
- グローシャドウ強化
- グラデーションスライドアニメーション

#### カードホバー
- `translateY(-6px)`: 大きめの浮き上がり
- トップボーダーグラデーション表示
- シャドウ・グロー強化

## レイアウト構成

### グリッドシステム

```css
.article-grid {
    display: grid;
    gap: 26px;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
}
```

### レスポンシブブレイクポイント

- **Desktop**: 1200px+
- **Tablet**: 640px - 960px
- **Mobile**: < 640px

## パフォーマンス最適化

### GPU アクセラレーション

```css
transform: translateY(-4px);
backdrop-filter: blur(20px);
```

`transform`と`backdrop-filter`でGPU処理を活用

### アニメーション最適化

```css
transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
```

カスタムイージング関数でスムーズなアニメーション

## アクセシビリティ

### フォーカス表示

```css
input:focus-visible {
    outline: none;
    border-color: var(--color-accent);
    box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.2);
}
```

### カラーコントラスト

- テキスト: `#e5e7eb` on `#0a0e27` (WCAG AA適合)
- アクセント: 十分なコントラスト比を確保

### スクリーンリーダー

```html
<label for="url" class="sr-only">スクレイピングするURLを入力</label>
```

## ダークモード最適化

### グロー効果

```css
box-shadow: 
    var(--shadow-md),
    0 0 30px rgba(139, 92, 246, 0.3);
```

ダークテーマに映えるグローエフェクト

### 透明度調整

```css
background: rgba(255, 255, 255, 0.03);  /* 極薄い白 */
background: rgba(139, 92, 246, 0.08);   /* アクセント */
```

## UI改善の要点

### Before → After

1. **背景**: 白無地 → ダークネイビー + アニメーショングロー
2. **カード**: フラットデザイン → グラスモーフィズム + ホバー効果
3. **ボタン**: 単色 → グラデーション + シャインアニメーション
4. **入力欄**: 白背景 → 半透明 + ブラー効果
5. **レイアウト**: 固定 → レスポンシブグリッド

### 技術的改善

- **CSS Variables**: テーマの一元管理
- **Modern Flexbox/Grid**: 柔軟なレイアウト
- **Transform/Filter**: GPU最適化
- **CSS Animations**: JavaScriptフリー
- **Mobile-First**: モバイル最適化

## ブラウザサポート

- Chrome/Edge: 90+
- Firefox: 88+
- Safari: 14+
- Mobile Safari: iOS 14+

## 今後の展開

- [ ] ダークモード切り替えボタン
- [ ] カスタムテーマ機能
- [ ] アニメーション速度設定
- [ ] 色覚異常対応モード
- [ ] ハイコントラストモード
