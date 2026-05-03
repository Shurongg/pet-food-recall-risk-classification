"""
Phase 9 — Inference: Predict Risk Labels for New Text

Loads the selected trained classifier and generates multi-label risk predictions
for a single recall description provided via CLI arguments.

Used by the Gradio app (app/app.py) as the backend prediction function.

Outputs clean JSON with:
  input_text, predicted_labels, scores, thresholds, low_confidence
"""

import argparse
import json
import os
import sys

import joblib
import numpy as np
from sentence_transformers import SentenceTransformer

sys.path.insert(0, os.path.dirname(__file__))
from config import EMBEDDING_MODEL_NAME, FINAL_LABEL_COLUMNS, INPUT_TEXT_TEMPLATE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict risk labels for a new pet food recall description."
    )
    parser.add_argument("--brand", required=True, help="Brand name(s)")
    parser.add_argument("--product", required=True, help="Product description")
    parser.add_argument("--reason", required=True, help="Recall reason description")
    parser.add_argument(
        "--model-dir",
        default="models/selected/",
        help="Directory containing model_config.json and thresholds.json (default: models/selected/)",
    )
    return parser.parse_args()


def predict(brand: str, product: str, reason: str, model_dir: str = "models/selected/") -> dict:
    """Return predicted risk labels for the given recall description fields.

    Returns a dict with keys:
      input_text, predicted_labels, scores, thresholds, low_confidence
    """
    # Load model config and thresholds
    with open(os.path.join(model_dir, "model_config.json"), encoding="utf-8") as f:
        model_config = json.load(f)
    with open(os.path.join(model_dir, "thresholds.json"), encoding="utf-8") as f:
        thresholds_data = json.load(f)

    thresholds = thresholds_data["thresholds"]
    model_path = model_config["model_path"]

    # Build input text
    text = INPUT_TEXT_TEMPLATE.format(
        brand_names=brand,
        product_description=product,
        recall_reason_description=reason,
    )

    # Encode with frozen sentence transformer
    encoder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    embedding = encoder.encode([text])  # shape (1, 384)

    # Load selected classifier and predict per-label probabilities
    clf = joblib.load(model_path)
    proba = clf.predict_proba(embedding)[0]  # shape (n_labels,), order = FINAL_LABEL_COLUMNS

    # Apply per-label thresholds
    predicted_labels = []
    scores = {}
    for i, label in enumerate(FINAL_LABEL_COLUMNS):
        score = float(proba[i])
        scores[label] = round(score, 4)
        if score >= thresholds[label]:
            predicted_labels.append(label)

    # Fallback: if nothing clears threshold, return the top-scoring label
    low_confidence = False
    if not predicted_labels:
        top_label = FINAL_LABEL_COLUMNS[int(np.argmax(proba))]
        predicted_labels = [top_label]
        low_confidence = True

    return {
        "input_text": text,
        "predicted_labels": predicted_labels,
        "scores": scores,
        "thresholds": {label: thresholds[label] for label in FINAL_LABEL_COLUMNS},
        "low_confidence": low_confidence,
    }


def main() -> None:
    args = parse_args()
    result = predict(
        brand=args.brand,
        product=args.product,
        reason=args.reason,
        model_dir=args.model_dir,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
