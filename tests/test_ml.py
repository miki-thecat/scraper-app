from __future__ import annotations

from pathlib import Path

from ml import evaluate, train


def write_dataset(path: Path) -> None:
    rows = [
        "text,label",
        "最新のAIソフトウェア開発を手掛ける企業です,IT",
        "クラウドサービスを提供し、データセンターを運用しています,IT",
        "大手銀行グループとして法人向け融資を展開しています,金融",
        "資産運用と証券仲介を主力とする企業です,金融",
        "自動車部品の製造と輸出を行うメーカーです,製造業",
        "航空機向けエンジンを組み立てる工場を保有しています,製造業",
    ]
    path.write_text("\n".join(rows), encoding="utf-8")


def test_train_and_evaluate(tmp_path):
    train_csv = tmp_path / "train.csv"
    valid_csv = tmp_path / "valid.csv"
    write_dataset(train_csv)
    write_dataset(valid_csv)

    vector_path = tmp_path / "vectorizer.joblib"
    model_path = tmp_path / "model.joblib"

    # Patch保存先
    train.VECTORIZER_PATH = vector_path
    train.MODEL_PATH = model_path
    evaluate.VECTORIZER_PATH = vector_path
    evaluate.MODEL_PATH = model_path

    train.train(train_csv, valid_csv)
    assert vector_path.exists()
    assert model_path.exists()

    score = evaluate.evaluate(valid_csv, threshold=0.5)
    assert score >= 0.5
