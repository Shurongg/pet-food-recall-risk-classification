"""
Phase 5 — Custom Dataset Construction

Builds the final Hugging Face-ready CSV dataset from consolidated labeled
recalls and creates train / validation / test splits. This phase does not
embed, train, evaluate, or synthesize data.
"""

import argparse
import csv
import json
import os
import random
import sys
from datetime import datetime, timezone
from typing import Any

from config import FINAL_LABEL_COLUMNS, INPUT_TEXT_TEMPLATE, RANDOM_SEED


DATASET_COLUMNS = [
    "text",
    "final_labels",
    *FINAL_LABEL_COLUMNS,
    "source",
    "source_id",
    "date",
    "brand_names",
    "product_description",
    "recall_reason_description",
    "source_url",
    "raw_title",
    "raw_category",
    "raw_issue_or_hazard",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5: build processed dataset and train/validation/test splits."
    )
    parser.add_argument(
        "--input",
        default="data/interim/consolidated_labeled_recalls.csv",
        help="Consolidated labeled recalls CSV",
    )
    parser.add_argument(
        "--summary-input",
        default="data/interim/consolidated_label_summary.json",
        help="Consolidated label summary JSON",
    )
    parser.add_argument(
        "--output",
        default="data/processed/",
        help="Directory to save processed dataset files",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.15,
        help="Fraction of data for the test split",
    )
    parser.add_argument(
        "--val-size",
        type=float,
        default=0.15,
        help="Fraction of data for the validation split",
    )
    parser.add_argument(
        "--max-seed-retries",
        type=int,
        default=1000,
        help="Number of sequential seeds to search, starting at --seed-start",
    )
    parser.add_argument(
        "--seed-start",
        type=int,
        default=0,
        help="First seed to search for split selection",
    )
    parser.add_argument(
        "--min-eval-positives",
        type=int,
        default=2,
        help="Preferred minimum positives per final label in validation and test",
    )
    return parser.parse_args()


def load_csv(path: str) -> list[dict[str, str]]:
    if not os.path.exists(path):
        print(f"ERROR: missing input file — {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_json(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_csv(path: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Written → {path} ({len(rows):,} rows)")


def write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"  Written → {path}")


def clean_text(value: Any) -> str:
    return "" if value is None else " ".join(str(value).split())


def as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def build_text(row: dict[str, str]) -> str:
    return INPUT_TEXT_TEMPLATE.format(
        brand_names=clean_text(row.get("brand_names", "")),
        product_description=clean_text(row.get("product_description", "")),
        recall_reason_description=clean_text(row.get("recall_reason_description", "")),
    )


def normalize_row(row: dict[str, str]) -> dict[str, Any]:
    final_labels = [
        label for label in FINAL_LABEL_COLUMNS
        if as_int(row.get(label, 0))
    ]
    out: dict[str, Any] = {
        "text": build_text(row),
        "final_labels": ";".join(final_labels),
    }
    for label in FINAL_LABEL_COLUMNS:
        out[label] = as_int(row.get(label, 0))
    for column in DATASET_COLUMNS:
        if column not in out:
            out[column] = clean_text(row.get(column, ""))
    return out


def positive_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        label: sum(as_int(row.get(label, 0)) for row in rows)
        for label in FINAL_LABEL_COLUMNS
    }


def multi_label_rows(rows: list[dict[str, Any]]) -> int:
    return sum(
        1 for row in rows
        if sum(as_int(row.get(label, 0)) for label in FINAL_LABEL_COLUMNS) > 1
    )


def all_labels_present(rows: list[dict[str, Any]]) -> bool:
    counts = positive_counts(rows)
    return all(counts[label] >= 1 for label in FINAL_LABEL_COLUMNS)


def min_eval_label_count(splits: dict[str, list[dict[str, Any]]]) -> int:
    eval_counts = []
    for split_name in ["validation", "test"]:
        counts = positive_counts(splits[split_name])
        eval_counts.extend(counts[label] for label in FINAL_LABEL_COLUMNS)
    return min(eval_counts)


def split_score(splits: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    total_counts = positive_counts(
        splits["train"] + splits["validation"] + splits["test"]
    )
    split_fractions = {
        "train": len(splits["train"]) / sum(len(rows) for rows in splits.values()),
        "validation": len(splits["validation"]) / sum(len(rows) for rows in splits.values()),
        "test": len(splits["test"]) / sum(len(rows) for rows in splits.values()),
    }
    label_deviation = 0.0
    for split_name, rows in splits.items():
        counts = positive_counts(rows)
        for label in FINAL_LABEL_COLUMNS:
            expected = total_counts[label] * split_fractions[split_name]
            label_deviation += abs(counts[label] - expected)

    eval_min = min_eval_label_count(splits)
    eval_total = sum(
        positive_counts(splits[split_name])[label]
        for split_name in ["validation", "test"]
        for label in FINAL_LABEL_COLUMNS
    )
    train_min = min(positive_counts(splits["train"])[label] for label in FINAL_LABEL_COLUMNS)
    return {
        "eval_min_positive_count": eval_min,
        "eval_total_positives": eval_total,
        "train_min_positive_count": train_min,
        "label_balance_deviation": round(label_deviation, 6),
    }


def score_key(score: dict[str, Any]) -> tuple[Any, ...]:
    return (
        score["eval_min_positive_count"],
        -score["label_balance_deviation"],
        score["eval_total_positives"],
        score["train_min_positive_count"],
    )


def split_counts(total: int, val_size: float, test_size: float) -> tuple[int, int, int]:
    test_n = round(total * test_size)
    val_n = round(total * val_size)
    train_n = total - val_n - test_n
    if min(train_n, val_n, test_n) <= 0:
        raise ValueError("Split sizes must each contain at least one row.")
    return train_n, val_n, test_n


def split_once(
    rows: list[dict[str, Any]],
    seed: int,
    val_size: float,
    test_size: float,
) -> dict[str, list[dict[str, Any]]]:
    train_n, val_n, test_n = split_counts(len(rows), val_size, test_size)
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    train = shuffled[:train_n]
    validation = shuffled[train_n:train_n + val_n]
    test = shuffled[train_n + val_n:train_n + val_n + test_n]
    return {"train": train, "validation": validation, "test": test}


def find_split(
    rows: list[dict[str, Any]],
    val_size: float,
    test_size: float,
    seed_start: int,
    seed_count: int,
    min_eval_positives: int,
) -> tuple[dict[str, list[dict[str, Any]]], int, dict[str, Any]]:
    best_splits: dict[str, list[dict[str, Any]]] | None = None
    best_seed: int | None = None
    best_score: dict[str, Any] | None = None
    satisfying = 0

    for offset in range(seed_count):
        seed = seed_start + offset
        splits = split_once(rows, seed, val_size, test_size)
        if not all(all_labels_present(split_rows) for split_rows in splits.values()):
            continue

        score = split_score(splits)
        satisfies = score["eval_min_positive_count"] >= min_eval_positives
        if satisfies:
            satisfying += 1

        if best_score is None:
            best_splits, best_seed, best_score = splits, seed, score
            continue

        best_satisfies = best_score["eval_min_positive_count"] >= min_eval_positives
        if satisfies and not best_satisfies:
            best_splits, best_seed, best_score = splits, seed, score
        elif satisfies == best_satisfies and score_key(score) > score_key(best_score):
            best_splits, best_seed, best_score = splits, seed, score

    if best_splits is None or best_seed is None or best_score is None:
        raise RuntimeError(
            "Could not find any random split with at least one positive example "
            "for every final label in each split."
        )

    best_score = dict(best_score)
    best_score["searched_seed_start"] = seed_start
    best_score["searched_seed_count"] = seed_count
    best_score["searched_seed_end"] = seed_start + seed_count - 1
    best_score["satisfying_seed_count"] = satisfying
    best_score["minimum_positive_constraint"] = (
        f"At least {min_eval_positives} positives for every final label "
        "in both validation and test."
    )
    best_score["minimum_positive_constraint_satisfied"] = (
        best_score["eval_min_positive_count"] >= min_eval_positives
    )
    if best_score["minimum_positive_constraint_satisfied"]:
        best_score["selection_reason"] = (
            "Selected the satisfying seed with the best label-balance score."
        )
    else:
        best_score["selection_reason"] = (
            "No searched seed satisfied the preferred validation/test minimum; "
            "selected the best available seed by highest minimum eval positives "
            "and label-balance score."
        )
    return best_splits, best_seed, best_score


def split_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "rows": len(rows),
        "positive_count_per_label": positive_counts(rows),
        "rows_with_multiple_labels": multi_label_rows(rows),
    }


def build_summary(
    full_rows: list[dict[str, Any]],
    splits: dict[str, list[dict[str, Any]]],
    split_seed: int,
    split_selection: dict[str, Any],
    args: argparse.Namespace,
    consolidated_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "dataset_build_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase": "Phase 5.1 — Split Quality Improvement",
        "input_file": args.input,
        "consolidated_label_summary_input": args.summary_input,
        "uncertain_rows_excluded": True,
        "label_columns": FINAL_LABEL_COLUMNS,
        "text_template": INPUT_TEXT_TEMPLATE,
        "split_strategy": {
            "preferred_split": "70/15/15",
            "train_fraction": 1 - args.val_size - args.test_size,
            "validation_fraction": args.val_size,
            "test_fraction": args.test_size,
            "seed": split_seed,
            "requirement": (
                "Every final label has at least one positive example in each split; "
                "prefer at least two positives for every final label in validation and test."
            ),
            "selection": split_selection,
        },
        "source_phase_4_5_summary": {
            "final_labeled_rows": consolidated_summary.get("final_labeled_rows"),
            "uncertain_rows": consolidated_summary.get("uncertain_rows"),
            "positive_count_per_final_label": consolidated_summary.get("positive_count_per_final_label"),
        },
        "full_dataset": split_summary(full_rows),
        "splits": {
            name: split_summary(split_rows)
            for name, split_rows in splits.items()
        },
        "output_files": {
            "full_dataset": "data/processed/full_dataset.csv",
            "train": "data/processed/train.csv",
            "validation": "data/processed/validation.csv",
            "test": "data/processed/test.csv",
            "label_columns": "data/processed/label_columns.json",
            "dataset_summary": "data/processed/dataset_summary.json",
        },
        "constraints": [
            "No embeddings",
            "No model training",
            "No evaluation",
            "No synthetic data",
            "Interim files not overwritten",
        ],
    }


def print_summary(summary: dict[str, Any]) -> None:
    print("\n" + "=" * 82)
    print("PHASE 5.1 DATASET SUMMARY")
    print("=" * 82)
    print(f"  Total rows: {summary['full_dataset']['rows']}")
    print(f"  Split seed: {summary['split_strategy']['seed']}")
    selection = summary["split_strategy"]["selection"]
    print(
        "  Minimum-positive constraint satisfied: "
        f"{selection['minimum_positive_constraint_satisfied']}"
    )
    print(f"  Selection reason: {selection['selection_reason']}")
    print("\n  Split sizes and label counts:")
    for split_name in ["train", "validation", "test"]:
        split = summary["splits"][split_name]
        print(f"    {split_name:<10} rows={split['rows']:<3} multi-label rows={split['rows_with_multiple_labels']}")
        for label in FINAL_LABEL_COLUMNS:
            print(f"      {label:<35} {split['positive_count_per_label'][label]:>3}")
    print("=" * 82)
    print("  Stopped after saving processed dataset and summary.")
    print("=" * 82)


def main() -> None:
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)

    raw_rows = load_csv(args.input)
    consolidated_summary = load_json(args.summary_input)
    full_rows = [normalize_row(row) for row in raw_rows]

    missing_labels = [
        label for label in FINAL_LABEL_COLUMNS
        if positive_counts(full_rows)[label] == 0
    ]
    if missing_labels:
        raise RuntimeError(f"Missing positive examples for final labels: {missing_labels}")

    splits, split_seed, split_selection = find_split(
        full_rows,
        args.val_size,
        args.test_size,
        args.seed_start,
        args.max_seed_retries,
        args.min_eval_positives,
    )

    summary = build_summary(
        full_rows,
        splits,
        split_seed,
        split_selection,
        args,
        consolidated_summary,
    )

    print("[build_dataset] Starting Phase 5.1 split quality improvement")
    print(f"  Loaded {len(full_rows):,} consolidated labeled rows from {args.input}")
    print("\n  Writing processed dataset files…")
    write_csv(os.path.join(args.output, "full_dataset.csv"), full_rows, DATASET_COLUMNS)
    write_csv(os.path.join(args.output, "train.csv"), splits["train"], DATASET_COLUMNS)
    write_csv(os.path.join(args.output, "validation.csv"), splits["validation"], DATASET_COLUMNS)
    write_csv(os.path.join(args.output, "test.csv"), splits["test"], DATASET_COLUMNS)
    write_json(os.path.join(args.output, "label_columns.json"), FINAL_LABEL_COLUMNS)
    write_json(os.path.join(args.output, "dataset_summary.json"), summary)

    print_summary(summary)


if __name__ == "__main__":
    main()
