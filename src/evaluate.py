"""
Phase 8 — Final Test Evaluation

Evaluates the selected provisional model on the held-out test split exactly
once, using fixed validation-selected thresholds. This phase does not train,
tune thresholds, regenerate embeddings, change labels, or alter model selection.
"""

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from typing import Any

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    hamming_loss,
    multilabel_confusion_matrix,
    precision_recall_fscore_support,
)

from config import FINAL_LABEL_COLUMNS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the selected model on the held-out test set once."
    )
    parser.add_argument(
        "--models",
        default="models/",
        help="Directory containing selected model metadata and classifiers",
    )
    parser.add_argument(
        "--embeddings",
        default="data/embeddings/",
        help="Directory containing test_embeddings.npy",
    )
    parser.add_argument(
        "--processed",
        default="data/processed/",
        help="Directory containing test.csv and label_columns.json",
    )
    parser.add_argument(
        "--output",
        default="results/",
        help="Directory to save test evaluation reports",
    )
    return parser.parse_args()


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"  Written → {path}")


def load_csv(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Written → {path}")


def label_matrix(rows: list[dict[str, str]], labels: list[str]) -> np.ndarray:
    return np.asarray(
        [[int(row[label]) for label in labels] for row in rows],
        dtype=np.int64,
    )


def load_label_columns(path: str) -> list[str]:
    labels = load_json(path)
    if labels != FINAL_LABEL_COLUMNS:
        raise ValueError(f"label_columns.json does not match FINAL_LABEL_COLUMNS: {labels}")
    return labels


def load_thresholds(path: str, selected_model: str, labels: list[str]) -> dict[str, float] | None:
    if not os.path.exists(path):
        return None
    payload = load_json(path)
    if payload.get("model") != selected_model:
        raise ValueError(
            f"Threshold file model {payload.get('model')} does not match selected model {selected_model}"
        )
    if payload.get("label_columns") != labels:
        raise ValueError("Threshold label columns do not match processed label columns.")
    return {label: float(payload["thresholds"][label]) for label in labels}


def predict_with_thresholds(model: Any, x_test: np.ndarray, labels: list[str], thresholds: dict[str, float] | None) -> np.ndarray:
    if thresholds is None:
        return np.asarray(model.predict(x_test), dtype=int)

    if not callable(getattr(model, "predict_proba", None)):
        raise ValueError("Thresholds were provided but selected model does not support predict_proba.")

    probabilities = np.asarray(model.predict_proba(x_test))
    y_pred = np.zeros((x_test.shape[0], len(labels)), dtype=int)
    for idx, label in enumerate(labels):
        y_pred[:, idx] = (probabilities[:, idx] >= thresholds[label]).astype(int)
    return y_pred


def summary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "micro_f1": f1_score(y_true, y_pred, average="micro", zero_division=0),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "hamming_loss": hamming_loss(y_true, y_pred),
        "subset_accuracy": accuracy_score(y_true, y_pred),
    }


def per_label_rows(y_true: np.ndarray, y_pred: np.ndarray, labels: list[str]) -> list[dict[str, Any]]:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        average=None,
        zero_division=0,
    )
    rows = []
    for idx, label in enumerate(labels):
        rows.append({
            "label": label,
            "precision": precision[idx],
            "recall": recall[idx],
            "f1": f1[idx],
            "support": int(support[idx]),
        })
    return rows


def confusion_matrices(y_true: np.ndarray, y_pred: np.ndarray, labels: list[str]) -> dict[str, dict[str, int]]:
    matrices = multilabel_confusion_matrix(y_true, y_pred)
    output = {}
    for idx, label in enumerate(labels):
        tn, fp, fn, tp = matrices[idx].ravel()
        output[label] = {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        }
    return output


def label_names(row: np.ndarray, labels: list[str]) -> list[str]:
    return [label for label, value in zip(labels, row) if int(value)]


def misclassified_examples(
    rows: list[dict[str, str]],
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: list[str],
) -> list[dict[str, Any]]:
    examples = []
    for idx, row in enumerate(rows):
        if np.array_equal(y_true[idx], y_pred[idx]):
            continue
        examples.append({
            "row_index": idx,
            "source": row.get("source", ""),
            "source_id": row.get("source_id", ""),
            "text": row.get("text", ""),
            "true_labels": label_names(y_true[idx], labels),
            "predicted_labels": label_names(y_pred[idx], labels),
        })
    return examples


def print_summary(selected_model: str, metrics: dict[str, float], per_label: list[dict[str, Any]]) -> None:
    print("\n" + "=" * 78)
    print("PHASE 8 FINAL TEST METRICS")
    print("=" * 78)
    print(f"  Selected model:  {selected_model}")
    print(f"  Micro F1:        {metrics['micro_f1']:.3f}")
    print(f"  Macro F1:        {metrics['macro_f1']:.3f}")
    print(f"  Weighted F1:     {metrics['weighted_f1']:.3f}")
    print(f"  Hamming loss:    {metrics['hamming_loss']:.3f}")
    print(f"  Subset accuracy: {metrics['subset_accuracy']:.3f}")
    print("\n  Per-label F1:")
    for row in per_label:
        print(
            f"    {row['label']:<35} "
            f"P={row['precision']:.3f} R={row['recall']:.3f} F1={row['f1']:.3f} "
            f"support={row['support']}"
        )
    print("=" * 78)
    print("  Test set evaluated once. No model or threshold changes were made.")
    print("=" * 78)


def main() -> None:
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)

    selected_config_path = os.path.join(args.models, "selected", "model_config.json")
    thresholds_path = os.path.join(args.models, "selected", "thresholds.json")
    selected_config = load_json(selected_config_path)
    selected_model = selected_config["selected_model"]
    model_path = selected_config["model_path"]

    labels = load_label_columns(os.path.join(args.processed, "label_columns.json"))
    thresholds = load_thresholds(thresholds_path, selected_model, labels)

    x_test = np.load(os.path.join(args.embeddings, "test_embeddings.npy"))
    test_rows = load_csv(os.path.join(args.processed, "test.csv"))
    y_test = label_matrix(test_rows, labels)
    if x_test.shape[0] != y_test.shape[0]:
        raise ValueError(f"test row mismatch: X={x_test.shape}, y={y_test.shape}")

    model = joblib.load(model_path)
    y_pred = predict_with_thresholds(model, x_test, labels, thresholds)

    metrics = summary_metrics(y_test, y_pred)
    per_label = per_label_rows(y_test, y_pred, labels)
    matrices = confusion_matrices(y_test, y_pred, labels)
    report = classification_report(
        y_test,
        y_pred,
        target_names=labels,
        output_dict=True,
        zero_division=0,
    )
    examples = misclassified_examples(test_rows, y_test, y_pred, labels)

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    test_metrics = {
        "created_at": created_at,
        "phase": "Phase 8 — Final Test Evaluation",
        "selected_model": selected_model,
        "model_path": model_path,
        "thresholds": thresholds,
        "test_rows": len(test_rows),
        "label_columns": labels,
        "metrics": metrics,
        "misclassified_rows": len(examples),
        "constraints": [
            "Test set evaluated once",
            "No training",
            "No threshold tuning on test set",
            "No model selection changes based on test result",
            "No embeddings regeneration",
            "No label changes",
            "No synthetic data",
        ],
    }

    print("[evaluate] Starting Phase 8 final held-out test evaluation")
    print(f"  Selected model: {selected_model}")
    print(f"  Model path:     {model_path}")
    print(f"  Test rows:      {len(test_rows)}")
    print("\n  Writing test evaluation reports…")
    write_json(os.path.join(args.output, "test_metrics.json"), test_metrics)
    write_csv(
        os.path.join(args.output, "per_label_metrics.csv"),
        per_label,
        ["label", "precision", "recall", "f1", "support"],
    )
    write_json(os.path.join(args.output, "classification_report.json"), report)
    write_json(os.path.join(args.output, "multilabel_confusion_matrices.json"), matrices)

    print_summary(selected_model, metrics, per_label)


if __name__ == "__main__":
    main()
