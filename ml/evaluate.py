from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_VALID = BASE_DIR / "data" / "valid.csv"
VECTORIZER_PATH = BASE_DIR / "vectorizer.joblib"
MODEL_PATH = BASE_DIR / "model.joblib"


def load_dataset(path: Path):
    df = pd.read_csv(path)
    if not {"text", "label"}.issubset(df.columns):
        raise ValueError("CSVにはtext列とlabel列が必要です。")
    return df["text"].astype(str), df["label"].astype(str)


def evaluate(valid_csv: Path, threshold: float = 0.7) -> float:
    if not VECTORIZER_PATH.exists() or not MODEL_PATH.exists():
        raise FileNotFoundError("モデル/ベクトライザが存在しません。ml/train.py を実行してください。")

    vectorizer = joblib.load(VECTORIZER_PATH)
    model = joblib.load(MODEL_PATH)

    texts, labels = load_dataset(valid_csv)
    features = vectorizer.transform(texts)
    predictions = model.predict(features)

    acc = accuracy_score(labels, predictions)
    print(f"Accuracy: {acc:.3f}")
    print("Confusion matrix:\n", confusion_matrix(labels, predictions))
    print(classification_report(labels, predictions, zero_division=0))

    if acc < threshold:
        raise AssertionError(f"Accuracy {acc:.3f} < {threshold}")
    return acc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate industry classifier")
    parser.add_argument("--valid", type=Path, default=DEFAULT_VALID)
    parser.add_argument("--threshold", type=float, default=0.7)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    evaluate(args.valid, args.threshold)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
