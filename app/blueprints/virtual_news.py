from flask import Blueprint, render_template, abort
from datetime import datetime

bp = Blueprint('virtual_news', __name__, url_prefix='/virtual-news')

ARTICLES = {
    "1": {
        "title": "【速報】AIエージェント、驚異的な進化を遂げる",
        "body": "最新のAIエージェント技術が発表され、世界中に衝撃を与えています。従来のモデルを遥かに凌駕する推論能力と、自律的なタスク実行能力を兼ね備えており、様々な分野での応用が期待されています。\n\n開発チームによると、この新しいエージェントは複雑なコーディングタスクも難なくこなし、人間の開発者とペアプログラミングを行うことも可能だといいます。",
        "published_at": "2025-11-30T10:00:00",
        "image": "ai_agent.jpg"
    },
    "2": {
        "title": "次世代Webフレームワーク「Flask-Next」が登場か？",
        "body": "PythonのWebフレームワーク界隈で、新たな噂が飛び交っています。「Flask-Next」と呼ばれるこのフレームワークは、FlaskのシンプルさとNext.jsのようなモダンな機能を併せ持つとされています。\n\nまだ公式な発表はありませんが、GitHub上での活動から、その存在はほぼ確実視されています。",
        "published_at": "2025-11-29T15:30:00",
        "image": "framework.jpg"
    },
    "3": {
        "title": "プログラミング言語「Python 4.0」のロードマップが流出",
        "body": "Python 4.0のロードマップとされる文書がネット上に流出しました。それによると、GIL（Global Interpreter Lock）の完全撤廃や、JITコンパイラの標準搭載など、パフォーマンス向上が主眼に置かれているようです。\n\nコミュニティでは賛否両論の議論が巻き起こっています。",
        "published_at": "2025-11-28T09:15:00",
        "image": "python.jpg"
    },
     "4": {
        "title": "リモートワーク時代の新しい働き方「メタバースオフィス」",
        "body": "VR技術の進化により、メタバース空間でのオフィスワークが現実味を帯びてきました。物理的な距離を感じさせないコミュニケーションが可能になり、チームの結束力が高まると報告されています。\n\n一部の企業では既に試験導入が始まっており、今後の普及が注目されます。",
        "published_at": "2025-11-27T18:45:00",
        "image": "metaverse.jpg"
    },
    "5": {
        "title": "量子コンピュータ、ついに家庭用モデルが発売へ",
        "body": "夢の技術とされていた量子コンピュータが、ついに家庭用モデルとして発売されることが決定しました。価格はまだ未定ですが、既存のPCを遥かに凌ぐ計算能力を持つとされています。\n\nゲームや動画編集だけでなく、個人のAIアシスタントの運用など、その用途は無限大です。",
        "published_at": "2025-11-26T12:00:00",
        "image": "quantum.jpg"
    }
}

@bp.route('/')
def index():
    # 辞書をリストに変換してテンプレートに渡す
    articles_list = [{"id": k, **v} for k, v in ARTICLES.items()]
    # 日付順にソート
    articles_list.sort(key=lambda x: x['published_at'], reverse=True)
    return render_template('virtual_news/index.html', articles=articles_list)

@bp.route('/article/<article_id>')
def article(article_id):
    article_data = ARTICLES.get(article_id)
    if not article_data:
        abort(404)

    # 日付文字列をdatetimeオブジェクトに変換（表示用）
    published_dt = datetime.fromisoformat(article_data['published_at'])

    return render_template('virtual_news/article.html', article=article_data, published_dt=published_dt)
