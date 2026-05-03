"""
Phase 7 — Classifier Training

Trains several multi-label classifiers on frozen transformer embeddings and
evaluates them on the validation split only. This phase does not run test-set
evaluation, regenerate embeddings, change labels, or create synthetic data.
"""

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from typing import Any

import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    hamming_loss,
    precision_recall_fscore_support,
)
from sklearn.multiclass import OneVsRestClassifier
from sklearn.svm import LinearSVC

from config import FINAL_LABEL_COLUMNS, RANDOM_SEED


THRESHOLD_GRID = np.round(np.arange(0.20, 0.801, 0.05), 2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train multi-label classifiers on saved sentence embeddings."
    )
    parser.add_argument(
        "--embeddings",
        default="data/embeddings/",
        help="Directory containing train/validation embedding arrays",
    )
    parser.add_argument(
        "--processed",
        default="data/processed/",
        help="Directory containing train/validation CSVs and label_columns.json",
    )
    parser.add_argument(
        "--output",
        default="models/",
        help="Directory to save trained classifiers and selection metadata",
    )
    parser.add_argument(
        "--results",
        default="results/",
        help="Directory to save validation metrics CSVs",
    )
    return parser.parse_args()


def load_csv(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_label_columns(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        labels = json.load(f)
    if labels != FINAL_LABEL_COLUMNS:
        raise ValueError(
            f"label_columns.json does not match FINAL_LABEL_COLUMNS: {labels}"
        )
    return labels


def label_matrix(rows: list[dict[str, str]], labels: list[str]) -> np.ndarray:
    return np.asarray(
        [[int(row[label]) for label in labels] for row in rows],
        dtype=np.int64,
    )


def load_inputs(embeddings_dir: str, processed_dir: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    labels = load_label_columns(os.path.join(processed_dir, "label_columns.json"))
    train_rows = load_csv(os.path.join(processed_dir, "train.csv"))
    val_rows = load_csv(os.path.join(processed_dir, "validation.csv"))

    x_train = np.load(os.path.join(embeddings_dir, "train_embeddings.npy"))
    x_val = np.load(os.path.join(embeddings_dir, "validation_embeddings.npy"))
    y_train = label_matrix(train_rows, labels)
    y_val = label_matrix(val_rows, labels)

    if x_train.shape[0] != y_train.shape[0]:
        raise ValueError(f"train row mismatch: X={x_train.shape}, y={y_train.shape}")
    if x_val.shape[0] != y_val.shape[0]:
        raise ValueError(f"validation row mismatch: X={x_val.shape}, y={y_val.shape}")
    if x_train.shape[1] != x_val.shape[1]:
        raise ValueError(f"embedding dimension mismatch: train={x_train.shape}, val={x_val.shape}")

    return x_train, y_train, x_val, y_val, labels


def build_models() -> dict[str, Any]:
    return {
        "dummy_most_frequent": OneVsRestClassifier(
            DummyClassifier(strategy="most_frequent")
        ),
        "logistic_regression": OneVsRestClassifier(
            LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                random_state=RANDOM_SEED,
                solver="liblinear",
            )
        ),
        "linear_svc": OneVsRestClassifier(
            LinearSVC(
                class_weight="balanced",
                random_state=RANDOM_SEED,
                max_iter=10000,
            )
        ),
        "random_forest": OneVsRestClassifier(
            RandomForestClassifier(
                n_estimators=300,
                class_weight="balanced",
                random_state=RANDOM_SEED,
                n_jobs=-1,
            )
        ),
    }


def has_predict_proba(model: Any) -> bool:
    return callable(getattr(model, "predict_proba", None))


def tune_thresholds(y_true: np.ndarray, probabilities: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    thresholds = []
    y_pred = np.zeros_like(y_true)

    for label_idx in range(y_true.shape[1]):
        best_threshold = 0.5
        best_f1 = -1.0
        label_true = y_true[:, label_idx]
        label_prob = probabilities[:, label_idx]

        for threshold in THRESHOLD_GRID:
            label_pred = (label_prob >= threshold).astype(int)
            f1 = f1_score(label_true, label_pred, zero_division=0)
            is_better = f1 > best_f1
            is_tie_closer_to_default = (
                f1 == best_f1 and abs(float(threshold) - 0.5) < abs(best_threshold - 0.5)
            )
            if is_better or is_tie_closer_to_default:
                best_f1 = f1
                best_threshold = float(threshold)

        thresholds.append(best_threshold)
        y_pred[:, label_idx] = (label_prob >= best_threshold).astype(int)

    return np.asarray(thresholds, dtype=float), y_pred


def predict_validation(model: Any, x_val: np.ndarray, y_val: np.ndarray) -> tuple[np.ndarray, list[float] | None, str]:
    if has_predict_proba(model):
        probabilities = model.predict_proba(x_val)
        probabilities = np.asarray(probabilities)
        thresholds, y_pred = tune_thresholds(y_val, probabilities)
        return y_pred, thresholds.tolist(), "predict_proba_threshold_tuned"

    y_pred = np.asarray(model.predict(x_val), dtype=int)
    return y_pred, None, "default_binary_predictions"


def summary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "micro_f1": f1_score(y_true, y_pred, average="micro", zero_division=0),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "hamming_loss": hamming_loss(y_true, y_pred),
        "subset_accuracy": accuracy_score(y_true, y_pred),
    }


def per_label_metrics(model_name: str, y_true: np.ndarray, y_pred: np.ndarray, labels: list[str]) -> list[dict[str, Any]]:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        average=None,
        zero_division=0,
    )
    rows = []
    for idx, label in enumerate(labels):
        rows.append({
            "model": model_name,
            "label": label,
            "precision": precision[idx],
            "recall": recall[idx],
            "f1": f1[idx],
            "support": int(support[idx]),
        })
    return rows


def write_csv(path: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Written → {path}")


def write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"  Written → {path}")


def train_and_validate(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    labels: list[str],
    classifier_dir: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    models = build_models()
    summary_rows: list[dict[str, Any]] = []
    per_label_rows: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase": "Phase 7 — Classifier Training",
        "label_columns": labels,
        "train_shape": list(x_train.shape),
        "validation_shape": list(x_val.shape),
        "models": {},
        "constraints": [
            "No test-set evaluation",
            "No embeddings regeneration",
            "No label changes",
            "No synthetic data",
            "Processed CSVs not modified",
        ],
    }

    for model_name, model in models.items():
        print(f"  Training {model_name}…")
        model.fit(x_train, y_train)
        y_pred, thresholds, prediction_method = predict_validation(model, x_val, y_val)
        metrics = summary_metrics(y_val, y_pred)

        model_path = os.path.join(classifier_dir, f"{model_name}.joblib")
        joblib.dump(model, model_path)

        summary_row = {
            "model": model_name,
            **metrics,
            "prediction_method": prediction_method,
            "thresholds": "" if thresholds is None else ";".join(f"{t:.2f}" for t in thresholds),
            "model_path": model_path,
        }
        summary_rows.append(summary_row)
        per_label_rows.extend(per_label_metrics(model_name, y_val, y_pred, labels))

        metadata["models"][model_name] = {
            "model_path": model_path,
            "prediction_method": prediction_method,
            "thresholds": thresholds,
            "validation_metrics": metrics,
        }

    return summary_rows, per_label_rows, metadata


def select_best_model(summary_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        summary_rows,
        key=lambda row: (
            row["macro_f1"],
            row["micro_f1"],
            row["weighted_f1"],
            row["subset_accuracy"],
            -row["hamming_loss"],
        ),
    )


def print_metrics_table(summary_rows: list[dict[str, Any]], selected_model: str) -> None:
    print("\n" + "=" * 112)
    print("PHASE 7 VALIDATION METRICS")
    print("=" * 112)
    print(
        f"  {'model':<24} {'micro_f1':>8} {'macro_f1':>8} {'weighted':>8} "
        f"{'hamming':>8} {'subset':>8} {'selected':>8}"
    )
    print(f"  {'-' * 24} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 8}")
    for row in sorted(summary_rows, key=lambda r: r["macro_f1"], reverse=True):
        print(
            f"  {row['model']:<24} "
            f"{row['micro_f1']:>8.3f} "
            f"{row['macro_f1']:>8.3f} "
            f"{row['weighted_f1']:>8.3f} "
            f"{row['hamming_loss']:>8.3f} "
            f"{row['subset_accuracy']:>8.3f} "
            f"{'*' if row['model'] == selected_model else '':>8}"
        )
    print("=" * 112)
    print(f"  Provisional best model: {selected_model}")
    print("  Test set was not evaluated.")
    print("=" * 112)


def main() -> None:
    args = parse_args()
    classifier_dir = os.path.join(args.output, "classifiers")
    selected_dir = os.path.join(args.output, "selected")
    os.makedirs(classifier_dir, exist_ok=True)
    os.makedirs(selected_dir, exist_ok=True)
    os.makedirs(args.results, exist_ok=True)

    x_train, y_train, x_val, y_val, labels = load_inputs(args.embeddings, args.processed)

    print("[train_classifiers] Starting Phase 7 validation-only classifier training")
    print(f"  X_train: {x_train.shape}  y_train: {y_train.shape}")
    print(f"  X_val:   {x_val.shape}  y_val:   {y_val.shape}")

    summary_rows, per_label_rows, metadata = train_and_validate(
        x_train,
        y_train,
        x_val,
        y_val,
        labels,
        classifier_dir,
    )

    best = select_best_model(summary_rows)
    best_model = best["model"]
    metadata["provisional_best_model"] = best_model
    metadata["selection_metric"] = "validation_macro_f1"

    summary_path = os.path.join(args.results, "validation_metrics_summary.csv")
    per_label_path = os.path.join(args.results, "validation_per_label_metrics.csv")
    metadata_path = os.path.join(classifier_dir, "classifier_metadata.json")
    write_csv(
        summary_path,
        summary_rows,
        [
            "model",
            "micro_f1",
            "macro_f1",
            "weighted_f1",
            "hamming_loss",
            "subset_accuracy",
            "prediction_method",
            "thresholds",
            "model_path",
        ],
    )
    write_csv(
        per_label_path,
        per_label_rows,
        ["model", "label", "precision", "recall", "f1", "support"],
    )
    write_json(metadata_path, metadata)

    selected_config = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase": "Phase 7 — Provisional Validation-Based Selection",
        "selected_model": best_model,
        "selection_metric": "validation_macro_f1",
        "validation_metrics": {
            key: best[key]
            for key in ["micro_f1", "macro_f1", "weighted_f1", "hamming_loss", "subset_accuracy"]
        },
        "model_path": best["model_path"],
        "prediction_method": best["prediction_method"],
        "test_evaluated": False,
    }
    write_json(os.path.join(selected_dir, "model_config.json"), selected_config)

    thresholds = metadata["models"][best_model]["thresholds"]
    thresholds_path = os.path.join(selected_dir, "thresholds.json")
    if thresholds is not None:
        write_json(
            thresholds_path,
            {
                "model": best_model,
                "label_columns": labels,
                "thresholds": dict(zip(labels, thresholds)),
            },
        )
    elif os.path.exists(thresholds_path):
        os.remove(thresholds_path)

    print_metrics_table(summary_rows, best_model)


if __name__ == "__main__":
    main()
