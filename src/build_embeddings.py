"""
Phase 6 — Sentence Embedding Generation

Encodes train / validation / test text with the frozen SentenceTransformer model
specified in config.py. This phase does not train classifiers, evaluate models,
change labels, or modify processed CSV files.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

import numpy as np

from config import EMBEDDING_MODEL_NAME


SPLITS = ["train", "validation", "test"]
TEXT_COLUMN = "text"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate frozen SentenceTransformer embeddings for dataset splits."
    )
    parser.add_argument(
        "--input",
        default="data/processed/",
        help="Directory containing train.csv, validation.csv, and test.csv",
    )
    parser.add_argument(
        "--output",
        default="data/embeddings/",
        help="Directory to save .npy embedding arrays and config JSON",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Encoding batch size",
    )
    return parser.parse_args()


def load_csv(path: str) -> list[dict[str, str]]:
    if not os.path.exists(path):
        print(f"ERROR: missing split CSV — {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_splits(input_dir: str) -> dict[str, list[dict[str, str]]]:
    rows_by_split = {}
    for split in SPLITS:
        path = os.path.join(input_dir, f"{split}.csv")
        rows = load_csv(path)
        if rows and TEXT_COLUMN not in rows[0]:
            print(f"ERROR: '{TEXT_COLUMN}' column missing from {path}", file=sys.stderr)
            sys.exit(1)
        rows_by_split[split] = rows
    return rows_by_split


def get_texts(rows: list[dict[str, str]]) -> list[str]:
    return [(row.get(TEXT_COLUMN) or "").strip() for row in rows]


def import_sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "sentence_transformers is not installed. Install project dependencies "
            "before running Phase 6, e.g. `python -m pip install sentence-transformers`."
        ) from exc
    return SentenceTransformer


def encode_split(model: Any, texts: list[str], batch_size: int) -> np.ndarray:
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=False,
    )
    return np.asarray(embeddings, dtype=np.float32)


def validate_embeddings(
    rows_by_split: dict[str, list[dict[str, str]]],
    embeddings_by_split: dict[str, np.ndarray],
) -> int:
    dimensions = set()
    for split in SPLITS:
        rows = rows_by_split[split]
        embeddings = embeddings_by_split[split]
        if embeddings.ndim != 2:
            raise ValueError(f"{split} embeddings must be 2D, got shape {embeddings.shape}")
        if embeddings.shape[0] != len(rows):
            raise ValueError(
                f"{split} row/embedding mismatch: {len(rows)} rows vs "
                f"{embeddings.shape[0]} embeddings"
            )
        dimensions.add(int(embeddings.shape[1]))

    if len(dimensions) != 1:
        raise ValueError(f"Inconsistent embedding dimensions across splits: {sorted(dimensions)}")
    return dimensions.pop()


def write_json(path: str, payload: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"  Written → {path}")


def main() -> None:
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)

    print("[build_embeddings] Starting Phase 6 frozen embedding generation")
    rows_by_split = load_splits(args.input)
    for split in SPLITS:
        print(f"  Loaded {split}: {len(rows_by_split[split]):,} rows")

    SentenceTransformer = import_sentence_transformer()
    print(f"  Loading model: {EMBEDDING_MODEL_NAME}")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    embeddings_by_split: dict[str, np.ndarray] = {}
    print("\n  Encoding texts…")
    for split in SPLITS:
        texts = get_texts(rows_by_split[split])
        embeddings = encode_split(model, texts, args.batch_size)
        embeddings_by_split[split] = embeddings
        print(f"    {split:<10} {embeddings.shape}")

    embedding_dimension = validate_embeddings(rows_by_split, embeddings_by_split)

    print("\n  Writing embedding files…")
    for split in SPLITS:
        path = os.path.join(args.output, f"{split}_embeddings.npy")
        np.save(path, embeddings_by_split[split])
        print(f"  Written → {path} {embeddings_by_split[split].shape}")

    config = {
        "embedding_model_name": EMBEDDING_MODEL_NAME,
        "embedding_dimension": embedding_dimension,
        "train_rows": len(rows_by_split["train"]),
        "validation_rows": len(rows_by_split["validation"]),
        "test_rows": len(rows_by_split["test"]),
        "text_column": TEXT_COLUMN,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    write_json(os.path.join(args.output, "embedding_config.json"), config)

    print("\n" + "=" * 72)
    print("PHASE 6 EMBEDDING SUMMARY")
    print("=" * 72)
    for split in SPLITS:
        print(f"  {split:<10} {embeddings_by_split[split].shape}")
    print(f"  embedding_dimension: {embedding_dimension}")
    print("=" * 72)
    print("  Stopped after embeddings were saved and validated.")
    print("=" * 72)


if __name__ == "__main__":
    main()
