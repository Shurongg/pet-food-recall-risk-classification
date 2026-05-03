"""
Phase 4 — Rule-Based Label Mapping and Uncertain Case Review

Assigns initial multi-label risk labels to strictly filtered recall records.
Rows with no clear rule match, vague-only wording, or ambiguity are separated
for later review. This phase does not train, embed, split, or create a final
dataset.
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any

from config import FINAL_LABEL_COLUMNS, LABEL_COLUMNS


TEXT_FIELDS = [
    "recall_reason_description",
    "raw_title",
    "raw_issue_or_hazard",
    "product_description",
    "raw_text",
]

OUTPUT_EXTRA_COLUMNS = [
    "labels",
    "label_evidence",
    "is_uncertain",
    "uncertainty_reason",
] + LABEL_COLUMNS

FINAL_LABEL_MAP = {
    "PATHOGEN_CONTAMINATION": ["PATHOGEN_CONTAMINATION"],
    "CHEMICAL_OR_NUTRITIONAL_RISK": [
        "MYCOTOXIN_OR_CHEMICAL_CONTAMINATION",
        "NUTRITIONAL_IMBALANCE_OR_TOXICITY",
    ],
    "PHYSICAL_OR_QUALITY_ISSUE": [
        "FOREIGN_MATERIAL_CONTAMINATION",
        "LABELING_OR_UNDECLARED_INGREDIENT_ISSUE",
        "QUALITY_OR_PROCESS_CONTROL_ISSUE",
    ],
}


RULE_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "PATHOGEN_CONTAMINATION": [
        (r"\bsalmonell+a\b|\bsalmonella\s+spp\.?\b|\bsalmonella\s+\w+\b", "Salmonella"),
        (r"\blisteria\b|\blisteria\s+monocytogenes\b|\blisteria\s+spp\.?\b", "Listeria"),
        (r"\be[\.\s-]*coli\b|\bescherichia\s+coli\b", "E. coli"),
        (r"\benterobacteriaceae\b", "Enterobacteriaceae"),
        (r"\bpathogenic\s+micro[- ]?organisms?\b", "pathogenic microorganisms"),
        (r"\bfoodborne\s+illness\b", "foodborne illness"),
        (r"\bmicrobial\s+hazard\b|\bmicrobiological\b", "microbial hazard"),
        (r"\bmesophiles?\s+aerobic\b|\baerobic\s+mesophiles?\b", "aerobic mesophiles"),
        (r"\bbird\s+flu\b|\bavian\s+influenza\b", "avian influenza"),
        (r"\bbacteria\b|\bbacterial\b|\bbacterium\b", "bacterial hazard"),
    ],
    "MYCOTOXIN_OR_CHEMICAL_CONTAMINATION": [
        (r"\baflatoxin\b|\bmycotoxin\b|\bvomitoxin\b|\bdeoxynivalenol\b|\bDON\b", "mycotoxin"),
        (r"\bpesticide\s+residues?\b|\bpesticide\b", "pesticide residue"),
        (r"\bethylen[e]?\s+oxide\b", "ethylene oxide"),
        (r"\bchlorpyrifos\b", "chlorpyrifos"),
        (r"\blead\s+(?:high|contamination|content|poisoning)\b|\b(?:high\s+content|contamination)\s+of\s+lead\b|\bheavy\s+metals?\b|\bmercury\b|\bcadmium\b|\barsenic\b", "heavy metal"),
        (r"\bcannabidiol\b|\bcbd\b", "cannabidiol"),
        (r"\bchemical\s+hazard\b|\bchemical\s+contamination\b", "chemical hazard"),
        (r"\bunauthori[sz]ed\s+(?:feed\s+)?additives?\b|\bnon[- ]?approved\s+(?:feed\s+)?additives?\b", "unauthorized feed additive"),
        (r"\bfeed\s+additives?\b", "feed additive"),
        (r"\bdrug\s+residue\b|\bresidue\b", "residue"),
    ],
    "NUTRITIONAL_IMBALANCE_OR_TOXICITY": [
        (r"\bvitamin\s+d3?\b|\bvit\.?\s*d3?\b", "vitamin D"),
        (r"\bvitamin\s+a\b|\bvit\.?\s*a\b", "vitamin A"),
        (r"\bthiamine\b|\bvitamin\s+b1\b|\bvit\.?\s*b1\b", "thiamine / vitamin B1"),
        (r"\bvitamin\s+k1\b|\bvit\.?\s*k1\b", "vitamin K1"),
        (r"\bzinc\b|\bcopper\b|\biron\b|\bcalcium\b|\bphosphorus\b|\bcobalt\b", "mineral/nutrient"),
        (r"\belevated\s+levels?\s+of\s+vitamin\b|\bhigh\s+content\s+of\s+vitamin\b", "elevated vitamin level"),
        (r"\btoo\s+high\s+content\s+of\s+vitamin\b|\bexceeding\s+amount\s+of\s+vitamin\b", "excess vitamin level"),
        (r"\blow\s+levels?\s+of\s+thiamine\b|\binsufficient\s+thiamine\b|\bdeficien(?:t|cy)\b", "nutrient deficiency"),
    ],
    "FOREIGN_MATERIAL_CONTAMINATION": [
        (r"\bforeign\s+(?:material|body|object|bodies)\b", "foreign material/body"),
        (r"\bsharp\s+pieces?\b", "sharp pieces"),
        (r"\bmetal\s+(?:objects?|pieces?|fragments?|particles?)\b|\bpieces?\s+of\s+metal\b|\bloose\s+metal\b", "metal object/piece"),
        (r"\bfragments?\s+metal\b", "metal fragments"),
        (r"\bplastic\s+(?:pieces?|fragments?)\b|\bplastic\s+contamination\b", "plastic piece/contamination"),
        (r"\bglass\s+(?:pieces?|fragments?)\b", "glass piece/fragment"),
        (r"\bporcelain\s+pieces?\b", "porcelain pieces"),
        (r"\bbone\s+(?:pieces?|fragments?)\b|\blarge\s+pieces?\s+of\s+bone\b", "bone pieces/fragments"),
        (r"\bsharp\s+foreign\s+body\b", "sharp foreign body"),
    ],
    "LABELING_OR_UNDECLARED_INGREDIENT_ISSUE": [
        (r"\bundeclared\b|\bnot\s+declared\b|\bfails?\s+to\s+declare\b", "undeclared ingredient/allergen"),
        (r"\ballergen\b|\ballergy\b|\ballergic\b", "allergen"),
        (r"\bmislabell?ed\b|\blabell?ing\s+error\b|\bincorrect\s+label\b", "labeling error"),
        (r"\bno\s+labell?ing\b|\bwithout\s+warning\s+(?:on|for)\s+.*label\b", "missing label/warning"),
        (r"\blabel\b.*\bwarning\b|\bwarning\b.*\blabel\b", "label warning issue"),
    ],
    "QUALITY_OR_PROCESS_CONTROL_ISSUE": [
        (r"\binsanitary\b|\binsanitary\s+conditions\b", "insanitary condition"),
        (r"\bstorage\s+process\b|\bstorage\s+conditions\b", "storage process issue"),
        (r"\bdefective\s+closure\b|\bpackaging\s+failure\b|\bpackaging\s+defect\b", "packaging/closure defect"),
        (r"\bprocess\s+deviation\b|\bmanufacturing\s+defect\b|\bgmp\b", "manufacturing/process issue"),
        (r"\bofficial\s+controls?\b|\bnot\s+subjected\s+to\s+official\s+controls?\b", "official controls issue"),
        (r"\bveterinar\w*\s+checks?\b|\bveterinair\w*\s+checks?\b|\bnecessary\s+veterinar\w*\s+checks?\b|\bnecessary\s+veterinair\w*\s+checks?\b", "veterinary checks issue"),
        (r"\binsufficient\s+checks?\b|\bskipped\s+.*checks?\b", "insufficient checks"),
        (r"\bunfavo[u]?rable\s+(?:documentary|identity)\s+check\b|\bdocumentary\s+check\b|\bidentity\s+check\b", "documentary/identity check"),
        (r"\billegal\s+import\b|\bunauthori[sz]ed\s+import\b", "illegal/unauthorized import"),
        (r"\bnot\s+inspected\b|\babsence\s+of\s+inspection\b", "inspection failure"),
        (r"\bhygiene\s+failure\b|\bdocument\s+failure\b", "hygiene/document failure"),
    ],
}


VAGUE_PHRASES = [
    r"\bpossible\s+contamination\b",
    r"\bpotential\s+contamination\b",
    r"\bpotentially\s+contaminated\b",
    r"\bmay\s+be\s+contaminated\b",
    r"\bquality\s+issue\b",
    r"\bout\s+of\s+an\s+abundance\s+of\s+caution\b",
    r"\bconsumer\s+complaint\b",
]


AMBIGUOUS_ONLY_PATTERNS = [
    r"\balert\s+notification\s+serious\b",
    r"\binformation\s+notification\s+for\s+(?:follow-up|attention)\b",
    r"\bborder\s+rejection\s+notification\b",
    r"\bnot\s+serious\b",
    r"\bundecided\b",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 4: apply rule-based multi-label risk mapping."
    )
    parser.add_argument(
        "--input",
        default="data/interim/filtered_recalls.csv",
        help="Filtered recalls CSV (default: data/interim/filtered_recalls.csv)",
    )
    parser.add_argument(
        "--output",
        default="data/interim/",
        help="Directory to save Phase 4 outputs (default: data/interim/)",
    )
    parser.add_argument(
        "--mode",
        choices=["map", "consolidate"],
        default="map",
        help=(
            "map: create detailed Phase 4 labels from filtered_recalls.csv; "
            "consolidate: create Phase 4.5 final labels from auto_labeled_recalls.csv"
        ),
    )
    parser.add_argument(
        "--uncertain",
        default="data/interim/uncertain_recalls.csv",
        help="Uncertain rows CSV used by --mode consolidate",
    )
    return parser.parse_args()


def load_csv(path: str) -> list[dict[str, str]]:
    if not os.path.exists(path):
        print(f"ERROR: missing input file — {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Written → {path} ({len(rows):,} rows)")


def write_json(path: str, payload: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"  Written → {path}")


def as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text).strip()


def label_text(row: dict[str, str]) -> str:
    return " ".join(clean_text(row.get(field, "")) for field in TEXT_FIELDS).lower()


def match_patterns(text: str) -> tuple[list[str], dict[str, list[str]]]:
    labels: list[str] = []
    evidence: dict[str, list[str]] = {}

    for label in LABEL_COLUMNS:
        hits = []
        for pattern, description in RULE_PATTERNS[label]:
            if re.search(pattern, text, flags=re.IGNORECASE):
                hits.append(description)
        if hits:
            labels.append(label)
            evidence[label] = sorted(set(hits))

    return labels, evidence


def has_any(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def uncertainty_reason(labels: list[str], text: str) -> str:
    if not labels:
        if has_any(VAGUE_PHRASES, text):
            return "vague-only wording without a clear risk cause"
        if has_any(AMBIGUOUS_ONLY_PATTERNS, text):
            return "regulatory notification text without a mappable hazard"
        return "no rule matched"

    if labels == ["QUALITY_OR_PROCESS_CONTROL_ISSUE"] and has_any(VAGUE_PHRASES, text):
        return "only vague quality/process wording matched"

    return ""


def format_evidence(evidence: dict[str, list[str]]) -> str:
    parts = []
    for label in LABEL_COLUMNS:
        hits = evidence.get(label, [])
        if hits:
            parts.append(f"{label}: {', '.join(hits)}")
    return " | ".join(parts)


def labeled_row(row: dict[str, str]) -> dict[str, Any]:
    text = label_text(row)
    labels, evidence = match_patterns(text)
    reason = uncertainty_reason(labels, text)
    is_uncertain = bool(reason)

    out: dict[str, Any] = dict(row)
    out["labels"] = ";".join(labels)
    out["label_evidence"] = format_evidence(evidence)
    out["is_uncertain"] = "1" if is_uncertain else "0"
    out["uncertainty_reason"] = reason
    for label in LABEL_COLUMNS:
        out[label] = 1 if label in labels else 0
    return out


def summarize(rows: list[dict[str, Any]], labeled: list[dict[str, Any]], uncertain: list[dict[str, Any]]) -> dict[str, Any]:
    positive_counts = {
        label: sum(int(row[label]) for row in rows)
        for label in LABEL_COLUMNS
    }
    positive_counts_labeled_only = {
        label: sum(int(row[label]) for row in labeled)
        for label in LABEL_COLUMNS
    }
    uncertain_reasons: dict[str, int] = {}
    for row in uncertain:
        reason = row["uncertainty_reason"]
        uncertain_reasons[reason] = uncertain_reasons.get(reason, 0) + 1

    return {
        "label_mapping_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase": "Phase 4 — Label Mapping and Uncertain Case Review",
        "input_file": "data/interim/filtered_recalls.csv",
        "outputs": {
            "auto_labeled_recalls": "data/interim/auto_labeled_recalls.csv",
            "uncertain_recalls": "data/interim/uncertain_recalls.csv",
        },
        "total_rows": len(rows),
        "labeled_rows": len(labeled),
        "uncertain_rows": len(uncertain),
        "rows_with_multiple_labels": sum(
            1 for row in labeled if sum(int(row[label]) for label in LABEL_COLUMNS) > 1
        ),
        "positive_count_per_label": positive_counts,
        "positive_count_per_label_labeled_rows_only": positive_counts_labeled_only,
        "uncertain_reason_counts": uncertain_reasons,
        "rule_patterns": {
            label: [
                {"pattern": pattern, "description": description}
                for pattern, description in RULE_PATTERNS[label]
            ]
            for label in LABEL_COLUMNS
        },
        "vague_uncertain_patterns": VAGUE_PHRASES,
        "ambiguous_notification_patterns": AMBIGUOUS_ONLY_PATTERNS,
        "constraints": [
            "No manual annotation in code",
            "No training",
            "No embeddings",
            "No train/validation/test split",
            "No synthetic data",
            "filtered_recalls.csv not overwritten",
        ],
    }


def print_summary(summary: dict[str, Any]) -> None:
    print("\n" + "=" * 76)
    print("PHASE 4 LABEL MAPPING SUMMARY")
    print("=" * 76)
    print(f"  Total rows:                {summary['total_rows']}")
    print(f"  Labeled rows:              {summary['labeled_rows']}")
    print(f"  Uncertain rows:            {summary['uncertain_rows']}")
    print(f"  Rows with multiple labels: {summary['rows_with_multiple_labels']}")
    print("\n  Positive count per label (including uncertain rows with tentative matches):")
    for label in LABEL_COLUMNS:
        print(f"    {label:<45} {summary['positive_count_per_label'][label]:>4}")
    print("=" * 76)
    print("  Stopped after rule-based label mapping and uncertain-case separation.")
    print("=" * 76)


def final_labels_for_row(row: dict[str, Any]) -> list[str]:
    final_labels = []
    for final_label in FINAL_LABEL_COLUMNS:
        detailed_sources = FINAL_LABEL_MAP[final_label]
        if any(as_int(row.get(detailed_label, 0)) for detailed_label in detailed_sources):
            final_labels.append(final_label)
    return final_labels


def consolidated_row(row: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = dict(row)
    final_labels = final_labels_for_row(out)
    out["final_labels"] = ";".join(final_labels)
    for final_label in FINAL_LABEL_COLUMNS:
        out[final_label] = 1 if final_label in final_labels else 0
    return out


def summarize_consolidation(
    consolidated: list[dict[str, Any]],
    uncertain: list[dict[str, str]],
    input_path: str,
    uncertain_path: str,
) -> dict[str, Any]:
    positive_counts = {
        label: sum(as_int(row.get(label, 0)) for row in consolidated)
        for label in FINAL_LABEL_COLUMNS
    }
    detailed_positive_counts = {
        label: sum(as_int(row.get(label, 0)) for row in consolidated)
        for label in LABEL_COLUMNS
    }
    return {
        "consolidation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase": "Phase 4.5 — Label Consolidation",
        "input_file": input_path,
        "uncertain_input_file": uncertain_path,
        "outputs": {
            "consolidated_labeled_recalls": "data/interim/consolidated_labeled_recalls.csv",
            "consolidated_label_summary": "data/interim/consolidated_label_summary.json",
        },
        "detailed_labels_preserved_in_input": True,
        "uncertain_rows_excluded": True,
        "final_label_columns": FINAL_LABEL_COLUMNS,
        "final_label_map": FINAL_LABEL_MAP,
        "final_labeled_rows": len(consolidated),
        "uncertain_rows": len(uncertain),
        "rows_with_multiple_final_labels": sum(
            1 for row in consolidated if sum(as_int(row.get(label, 0)) for label in FINAL_LABEL_COLUMNS) > 1
        ),
        "positive_count_per_final_label": positive_counts,
        "positive_count_per_detailed_label": detailed_positive_counts,
        "constraints": [
            "No training",
            "No embeddings",
            "No train/validation/test split",
            "No synthetic data",
            "auto_labeled_recalls.csv not overwritten",
            "uncertain_recalls.csv not overwritten",
        ],
    }


def print_consolidation_summary(summary: dict[str, Any]) -> None:
    print("\n" + "=" * 76)
    print("PHASE 4.5 LABEL CONSOLIDATION SUMMARY")
    print("=" * 76)
    print(f"  Final labeled rows:         {summary['final_labeled_rows']}")
    print(f"  Uncertain rows excluded:    {summary['uncertain_rows']}")
    print(f"  Rows with multiple labels:  {summary['rows_with_multiple_final_labels']}")
    print("\n  Positive count per final label:")
    for label in FINAL_LABEL_COLUMNS:
        print(f"    {label:<35} {summary['positive_count_per_final_label'][label]:>4}")
    print("=" * 76)
    print("  Stopped after label consolidation and summary.")
    print("=" * 76)


def run_detailed_mapping(args: argparse.Namespace) -> None:
    rows = load_csv(args.input)
    mapped = [labeled_row(row) for row in rows]
    labeled = [row for row in mapped if row["is_uncertain"] == "0"]
    uncertain = [row for row in mapped if row["is_uncertain"] == "1"]

    input_columns = list(rows[0].keys()) if rows else []
    output_columns = input_columns + [c for c in OUTPUT_EXTRA_COLUMNS if c not in input_columns]

    auto_path = os.path.join(args.output, "auto_labeled_recalls.csv")
    uncertain_path = os.path.join(args.output, "uncertain_recalls.csv")
    summary_path = os.path.join(args.output, "label_mapping_summary.json")

    print("[label_mapping] Starting Phase 4 rule-based label mapping")
    print(f"  Loaded {len(rows):,} filtered rows from {args.input}")
    print("\n  Writing Phase 4 outputs…")
    write_csv(auto_path, labeled, output_columns)
    write_csv(uncertain_path, uncertain, output_columns)

    summary = summarize(mapped, labeled, uncertain)
    write_json(summary_path, summary)
    print_summary(summary)


def run_consolidation(args: argparse.Namespace) -> None:
    rows = load_csv(args.input)
    uncertain = load_csv(args.uncertain)
    consolidated = [consolidated_row(row) for row in rows]

    input_columns = list(rows[0].keys()) if rows else []
    output_columns = (
        input_columns
        + ["final_labels"]
        + [label for label in FINAL_LABEL_COLUMNS if label not in input_columns]
    )

    consolidated_path = os.path.join(args.output, "consolidated_labeled_recalls.csv")
    summary_path = os.path.join(args.output, "consolidated_label_summary.json")

    print("[label_mapping] Starting Phase 4.5 label consolidation")
    print(f"  Loaded {len(rows):,} auto-labeled rows from {args.input}")
    print(f"  Loaded {len(uncertain):,} uncertain rows from {args.uncertain}")
    print("\n  Writing Phase 4.5 outputs…")
    write_csv(consolidated_path, consolidated, output_columns)

    summary = summarize_consolidation(consolidated, uncertain, args.input, args.uncertain)
    write_json(summary_path, summary)
    print_consolidation_summary(summary)


def main() -> None:
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)

    if args.mode == "consolidate":
        run_consolidation(args)
    else:
        run_detailed_mapping(args)


if __name__ == "__main__":
    main()
