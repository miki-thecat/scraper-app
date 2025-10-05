from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_PATH = BASE_DIR / "ml" / "vectorizer.joblib"
MODEL_PATH = BASE_DIR / "ml" / "model.joblib"


def load_artifacts():
    if not VECTOR_PATH.exists() or not MODEL_PATH.exists():
        raise FileNotFoundError(
            "モデルファイルが見つかりません。ml/train.py を実行して生成してください。"
        )
    vectorizer = joblib.load(VECTOR_PATH)
    model = joblib.load(MODEL_PATH)
    return vectorizer, model


def main() -> int:
    try:
        vectorizer, model = load_artifacts()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    print("企業概要文を入力してください (終了: Ctrl+D)")
    try:
        text = sys.stdin.read().strip()
    except KeyboardInterrupt:
        return 0

    if not text:
        print("入力が空です。概要文を入力してください。", file=sys.stderr)
        return 1

    features = vectorizer.transform([text])
    prediction = model.predict(features)[0]
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(features)
        confidence = float(np.max(proba))
    else:
        confidence = None

    if confidence is not None:
        print(f"予測業界: {prediction} (確信度: {confidence:.2f})")
    else:
        print(f"予測業界: {prediction}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
