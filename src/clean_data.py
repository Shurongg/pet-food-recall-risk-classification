"""
Phase 3 — Cleaning and Scope Filtering

Loads raw recall rows from all inspected sources, applies strict pet-food scope
filtering, normalizes source-specific fields into common columns, and removes
conservative duplicates. This phase does not label, split, embed, train, or
create a final dataset.
"""

import argparse
import ast
import csv
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from typing import Any


STRICT_INCLUDE = [
    "pet food",
    "pet feed",
    "dog food",
    "cat food",
    "pet treat",
    "dog treat",
    "cat treat",
    "pet chew",
    "dog chew",
    "cat chew",
    "raw pet food",
    "food for dogs",
    "food for cats",
    "feed for dogs",
    "feed for cats",
]

STRICT_EXCLUDE = [
    "hot dog",
    "hotdog",
    "corn dog",
    "dogfish",
]

FILTERED_COLUMNS = [
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
    "raw_text",
    "scope_match",
    "dedup_key",
]

REJECTED_COLUMNS = FILTERED_COLUMNS + ["rejection_reason"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 3: strictly filter and normalize raw recall records into "
            "interim candidate files. No labels, splits, embeddings, or models."
        )
    )
    parser.add_argument(
        "--input",
        default="data/raw/",
        help="Directory containing raw source CSV files (default: data/raw/)",
    )
    parser.add_argument(
        "--output",
        default="data/interim/",
        help="Directory to save filtered outputs (default: data/interim/)",
    )
    parser.add_argument(
        "--counts",
        default="data/interim/source_candidate_counts.csv",
        help="Phase 2.6 source counts CSV for provenance checks",
    )
    return parser.parse_args()


def load_csv(path: str, encoding: str = "utf-8") -> list[dict[str, str]]:
    if not os.path.exists(path):
        print(f"  WARNING: file not found — {path}", file=sys.stderr)
        return []
    with open(path, newline="", encoding=encoding) as f:
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


def clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return re.sub(r"\s+", " ", text).strip()


def combined_text(row: dict[str, Any], fields: list[str]) -> str:
    return " ".join(clean_text(row.get(f, "")) for f in fields).strip()


def scope_status(text: str) -> tuple[bool, str]:
    lowered = text.lower()
    excluded = next((term for term in STRICT_EXCLUDE if term in lowered), None)
    if excluded:
        return False, f"excluded false positive: {excluded}"
    included = next((term for term in STRICT_INCLUDE if term in lowered), None)
    if included:
        return True, included
    return False, "no strict pet-food include term"


def normalize_date(value: str, source: str) -> str:
    text = clean_text(value)
    if not text:
        return ""

    formats = {
        "fda_cvm": ["%m/%d/%Y"],
        "rasff": ["%d-%m-%Y %H:%M:%S", "%d-%m-%Y"],
        "uk_fsa": ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z"],
        "openfda": ["%Y%m%d"],
        "canada": ["%Y-%m-%d"],
    }.get(source, [])

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return text[:10]


def normalize_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", clean_text(value))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_dictish(value: str) -> Any:
    text = clean_text(value)
    if not text:
        return None
    try:
        return ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return None


def extract_uk_products(value: str) -> str:
    text = clean_text(value)
    if not text:
        return ""

    products: list[str] = []
    for part in text.split(" | "):
        parsed = parse_dictish(part)
        if isinstance(parsed, dict):
            product = clean_text(parsed.get("productName", ""))
            if product:
                products.append(product)

    return " | ".join(products) if products else text


def extract_uk_problem(value: str) -> str:
    text = clean_text(value)
    parsed = parse_dictish(text)
    if not isinstance(parsed, dict):
        return text

    pieces = [clean_text(parsed.get("riskStatement", ""))]
    allergens = parsed.get("allergen")
    if isinstance(allergens, list):
        labels = [
            clean_text(a.get("label", ""))
            for a in allergens
            if isinstance(a, dict) and clean_text(a.get("label", ""))
        ]
        if labels:
            pieces.append("Allergens: " + ", ".join(labels))

    return " ".join(p for p in pieces if p).strip() or text


def extract_uk_business(value: str) -> str:
    parsed = parse_dictish(value)
    if isinstance(parsed, dict):
        return clean_text(parsed.get("commonName", ""))
    return clean_text(value)


def make_record(
    *,
    source: str,
    source_id: str,
    date: str,
    brand_names: str,
    product_description: str,
    recall_reason_description: str,
    source_url: str,
    raw_title: str,
    raw_category: str,
    raw_issue_or_hazard: str,
    raw_text: str,
    scope_match: str,
    rejection_reason: str = "",
) -> dict[str, str]:
    record = {
        "source": clean_text(source),
        "source_id": clean_text(source_id),
        "date": clean_text(date),
        "brand_names": clean_text(brand_names),
        "product_description": clean_text(product_description),
        "recall_reason_description": clean_text(recall_reason_description),
        "source_url": clean_text(source_url),
        "raw_title": clean_text(raw_title),
        "raw_category": clean_text(raw_category),
        "raw_issue_or_hazard": clean_text(raw_issue_or_hazard),
        "raw_text": clean_text(raw_text),
        "scope_match": clean_text(scope_match),
        "dedup_key": "",
    }
    record["dedup_key"] = build_dedup_key(record)
    if rejection_reason:
        record["rejection_reason"] = clean_text(rejection_reason)
    return record


def build_dedup_key(record: dict[str, str]) -> str:
    if record["source_id"]:
        return "source_id|" + normalize_key(record["source"]) + "|" + normalize_key(record["source_id"])

    parts = [
        record["product_description"],
        record["recall_reason_description"],
        record["date"],
    ]
    return "fallback|" + "|".join(normalize_key(p) for p in parts)


def normalize_fda(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    accepted, rejected = [], []
    source = "FDA CVM Animal & Veterinary Recalls"
    page_url = "https://www.fda.gov/animal-veterinary/safety-health/recalls-withdrawals"

    for row in rows:
        product = clean_text(row.get("Product-Description", ""))
        reason = clean_text(row.get("Recall-Reason-Description", ""))
        brand = clean_text(row.get("Brand-Names", ""))
        text = combined_text(row, ["Brand-Names", "Product-Description", "Recall-Reason-Description", "Company-Name"])
        in_scope, reason_text = scope_status(text)
        record = make_record(
            source=source,
            source_id="",
            date=normalize_date(row.get("Date", ""), "fda_cvm"),
            brand_names=brand,
            product_description=product,
            recall_reason_description=reason,
            source_url=page_url,
            raw_title=product,
            raw_category=clean_text(row.get("Terminated-Recall", "")),
            raw_issue_or_hazard=reason,
            raw_text=text,
            scope_match=reason_text if in_scope else "",
            rejection_reason="" if in_scope else reason_text,
        )
        (accepted if in_scope else rejected).append(record)

    return accepted, rejected


def normalize_rasff(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    accepted, rejected = [], []
    source = "EU RASFF Manual Export"
    page_url = "https://webgate.ec.europa.eu/rasff-window/screen/search"

    for row in rows:
        subject = clean_text(row.get("subject", ""))
        hazards = clean_text(row.get("hazards", ""))
        text = combined_text(row, ["subject", "category", "type", "hazards", "classification", "risk_decision", "origin"])
        in_scope, reason_text = scope_status(text)
        issue = hazards or clean_text(
            " ".join(
                p for p in [
                    row.get("classification", ""),
                    row.get("risk_decision", ""),
                    row.get("origin", ""),
                ]
                if p
            )
        )
        record = make_record(
            source=source,
            source_id=row.get("reference", ""),
            date=normalize_date(row.get("date", ""), "rasff"),
            brand_names="",
            product_description=subject,
            recall_reason_description=issue,
            source_url=page_url,
            raw_title=subject,
            raw_category=row.get("category", ""),
            raw_issue_or_hazard=hazards,
            raw_text=text,
            scope_match=reason_text if in_scope else "",
            rejection_reason="" if in_scope else reason_text,
        )
        (accepted if in_scope else rejected).append(record)

    return accepted, rejected


def normalize_uk_fsa(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    accepted, rejected = [], []
    source = "UK Food Standards Agency Food Alerts"

    for row in rows:
        title = clean_text(row.get("title", ""))
        product = extract_uk_products(row.get("productDetails", ""))
        issue = extract_uk_problem(row.get("problem", ""))
        text = " ".join([title, product, issue]).strip()
        in_scope, reason_text = scope_status(text)
        record = make_record(
            source=source,
            source_id=row.get("notation", "") or row.get("@id", ""),
            date=normalize_date(row.get("created", ""), "uk_fsa"),
            brand_names=extract_uk_business(row.get("reportingBusiness", "")),
            product_description=product or title,
            recall_reason_description=issue,
            source_url=row.get("alertURL", "") or row.get("@id", ""),
            raw_title=title,
            raw_category=row.get("type", ""),
            raw_issue_or_hazard=row.get("problem", ""),
            raw_text=text,
            scope_match=reason_text if in_scope else "",
            rejection_reason="" if in_scope else reason_text,
        )
        (accepted if in_scope else rejected).append(record)

    return accepted, rejected


def normalize_openfda(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    accepted, rejected = [], []
    source = "openFDA Food Enforcement API (multi-keyword)"
    page_url = "https://open.fda.gov/apis/food/enforcement/"

    for row in rows:
        product = clean_text(row.get("product_description", ""))
        reason = clean_text(row.get("reason_for_recall", ""))
        text = combined_text(row, ["product_description", "reason_for_recall", "recalling_firm", "product_type"])
        in_scope, reason_text = scope_status(text)
        record = make_record(
            source=source,
            source_id=row.get("recall_number", "") or row.get("event_id", ""),
            date=normalize_date(row.get("recall_initiation_date", ""), "openfda"),
            brand_names=row.get("recalling_firm", ""),
            product_description=product,
            recall_reason_description=reason,
            source_url=page_url,
            raw_title=product,
            raw_category=row.get("product_type", ""),
            raw_issue_or_hazard=reason,
            raw_text=text,
            scope_match=reason_text if in_scope else "",
            rejection_reason="" if in_scope else reason_text,
        )
        (accepted if in_scope else rejected).append(record)

    return accepted, rejected


def normalize_canada(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    accepted, rejected = [], []
    source = "Canada CFIA + Consumer Product Safety recalls"

    for row in rows:
        title = clean_text(row.get("Title", ""))
        product = clean_text(row.get("Product", "")) or title
        issue = clean_text(row.get("Issue", ""))
        text = combined_text(row, ["Title", "Product", "Issue", "Category"])
        in_scope, reason_text = scope_status(text)
        record = make_record(
            source=source,
            source_id=row.get("NID", ""),
            date=normalize_date(row.get("Last updated", ""), "canada"),
            brand_names="",
            product_description=product,
            recall_reason_description=issue,
            source_url=row.get("URL", ""),
            raw_title=title,
            raw_category=row.get("Category", ""),
            raw_issue_or_hazard=issue,
            raw_text=text,
            scope_match=reason_text if in_scope else "",
            rejection_reason="" if in_scope else reason_text,
        )
        (accepted if in_scope else rejected).append(record)

    return accepted, rejected


def deduplicate(records: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    seen: dict[str, dict[str, str]] = {}
    unique, duplicates = [], []
    for record in records:
        key = record["dedup_key"]
        if key in seen:
            duplicate = dict(record)
            duplicate["duplicate_of"] = seen[key].get("source_id", "") or seen[key]["dedup_key"]
            duplicates.append(duplicate)
            continue
        seen[key] = record
        unique.append(record)
    return unique, duplicates


def count_by_source(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        source = row["source"]
        counts[source] = counts.get(source, 0) + 1
    return counts


def build_summary(
    raw_counts: dict[str, int],
    candidates: list[dict[str, str]],
    filtered: list[dict[str, str]],
    rejected: list[dict[str, str]],
    duplicates: list[dict[str, str]],
    phase26_counts_path: str,
) -> dict[str, Any]:
    candidate_counts = count_by_source(candidates)
    filtered_counts = count_by_source(filtered)
    rejected_counts = count_by_source(rejected)
    duplicate_counts = count_by_source(duplicates)

    source_names = list(raw_counts.keys())
    by_source = {}
    for source in source_names:
        by_source[source] = {
            "raw_rows": raw_counts.get(source, 0),
            "strict_candidates_before_dedup": candidate_counts.get(source, 0),
            "rows_after_dedup": filtered_counts.get(source, 0),
            "rejected_scope_rows": rejected_counts.get(source, 0),
            "duplicate_rows_removed": duplicate_counts.get(source, 0),
        }

    return {
        "cleaning_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase": "Phase 3 — Cleaning and Scope Filtering",
        "source_expansion_closed": True,
        "phase26_counts_reference": phase26_counts_path,
        "scope_filter": {
            "include_terms": STRICT_INCLUDE,
            "exclude_false_positive_terms": STRICT_EXCLUDE,
            "method": "case-insensitive substring match on source-specific text fields",
        },
        "deduplication": {
            "method": (
                "conservative exact deduplication by source + source_id when available; "
                "otherwise normalized product_description + recall_reason_description + date"
            ),
            "duplicates_removed": len(duplicates),
            "duplicate_examples": duplicates[:10],
        },
        "columns": FILTERED_COLUMNS,
        "by_source": by_source,
        "totals": {
            "raw_rows": sum(raw_counts.values()),
            "strict_candidates_before_dedup": len(candidates),
            "rows_after_dedup": len(filtered),
            "rejected_scope_rows": len(rejected),
            "duplicate_rows_removed": len(duplicates),
        },
        "constraints": [
            "No label mapping",
            "No manual annotation",
            "No model code",
            "No synthetic data",
            "No train/validation/test split",
            "Raw files not modified",
        ],
    }


def print_counts(summary: dict[str, Any]) -> None:
    print("\n" + "=" * 82)
    print("PHASE 3 CLEANING SUMMARY")
    print("=" * 82)
    print(
        f"  {'Source':<48} {'Raw':>7} {'Strict':>8} "
        f"{'Deduped':>8} {'Rejected':>9}"
    )
    print(f"  {'-' * 48} {'-' * 7} {'-' * 8} {'-' * 8} {'-' * 9}")
    for source, counts in summary["by_source"].items():
        print(
            f"  {source:<48} "
            f"{counts['raw_rows']:>7} "
            f"{counts['strict_candidates_before_dedup']:>8} "
            f"{counts['rows_after_dedup']:>8} "
            f"{counts['rejected_scope_rows']:>9}"
        )
    totals = summary["totals"]
    print(f"  {'-' * 48} {'-' * 7} {'-' * 8} {'-' * 8} {'-' * 9}")
    print(
        f"  {'TOTAL':<48} "
        f"{totals['raw_rows']:>7} "
        f"{totals['strict_candidates_before_dedup']:>8} "
        f"{totals['rows_after_dedup']:>8} "
        f"{totals['rejected_scope_rows']:>9}"
    )
    print("=" * 82)
    print("  Stopped after cleaning and scope filtering.")
    print("=" * 82)


def main() -> None:
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)

    sources = [
        (
            "FDA CVM Animal & Veterinary Recalls",
            os.path.join(args.input, "fda_animal_veterinary_recalls.csv"),
            "utf-8",
            normalize_fda,
        ),
        (
            "EU RASFF Manual Export",
            os.path.join(args.input, "eu_rasff_pet_food_raw.csv"),
            "utf-8-sig",
            normalize_rasff,
        ),
        (
            "UK Food Standards Agency Food Alerts",
            os.path.join(args.input, "uk_fsa_food_alerts_raw.csv"),
            "utf-8",
            normalize_uk_fsa,
        ),
        (
            "openFDA Food Enforcement API (multi-keyword)",
            os.path.join(args.input, "openfda_pet_food_enforcement_raw.csv"),
            "utf-8",
            normalize_openfda,
        ),
        (
            "Canada CFIA + Consumer Product Safety recalls",
            os.path.join(args.input, "canada_cfia_recalls_raw.csv"),
            "utf-8",
            normalize_canada,
        ),
    ]

    raw_counts: dict[str, int] = {}
    candidates: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []

    print("[clean_data] Starting Phase 3 cleaning and strict scope filtering")
    for source_name, path, encoding, normalizer in sources:
        rows = load_csv(path, encoding=encoding)
        raw_counts[source_name] = len(rows)
        source_candidates, source_rejected = normalizer(rows)
        candidates.extend(source_candidates)
        rejected.extend(source_rejected)
        print(
            f"  {source_name}: {len(rows):,} raw, "
            f"{len(source_candidates):,} strict candidates, "
            f"{len(source_rejected):,} rejected"
        )

    filtered, duplicates = deduplicate(candidates)
    summary = build_summary(raw_counts, candidates, filtered, rejected, duplicates, args.counts)

    filtered_path = os.path.join(args.output, "filtered_recalls.csv")
    rejected_path = os.path.join(args.output, "rejected_scope_rows.csv")
    summary_path = os.path.join(args.output, "cleaning_summary.json")

    print("\n  Writing Phase 3 outputs…")
    write_csv(filtered_path, filtered, FILTERED_COLUMNS)
    write_csv(rejected_path, rejected, REJECTED_COLUMNS)
    write_json(summary_path, summary)

    print_counts(summary)


if __name__ == "__main__":
    main()
