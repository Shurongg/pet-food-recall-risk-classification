"""
Phase 2 / 2.6 — Data Inspection

Loads all raw sources, counts rows and missing values, estimates pet-food
candidate counts, and writes structured inspection outputs.

This script does NOT filter, clean, label, or modify any raw files.
The outputs are read-only summaries and notes to inform Phase 3 decisions.

Inputs  (--input, default: data/raw/):
  fda_animal_veterinary_recalls.csv
  eu_rasff_pet_food_raw.csv
  uk_fsa_food_alerts_raw.csv
  openfda_pet_food_enforcement_raw.csv
  canada_cfia_recalls_raw.csv
  source_inventory.csv

Outputs (--output, default: data/interim/):
  inspection_summary.json
  source_candidate_counts.csv

Also writes / updates:
  docs/data_inspection_notes.md
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Scope-filter term lists (Phase 2 inspection only — not final filters)
# ---------------------------------------------------------------------------

# Strict inclusion terms — used for UK FSA and openFDA (broad/noisy sources).
# A row is a candidate only if its text contains at least one of these phrases.
STRICT_INCLUDE = [
    "pet food",
    "pet feed",
    "dog food",
    "cat food",
    "dog treat",
    "cat treat",
    "pet treat",
    "pet chew",
    "dog chew",
    "cat chew",
    "raw pet food",
    "food for dogs",
    "food for cats",
    "feed for dogs",
    "feed for cats",
]

# False-positive exclusions applied before the include check.
STRICT_EXCLUDE = [
    "hot dog",
    "hotdog",
    "corn dog",
    "dogfish",
]

# Broad companion-animal terms — used for FDA CVM (already narrowed to animal/vet).
# A row is broadly in-scope if it matches any of these AND none of the
# clear out-of-scope markers below.
BROAD_INCLUDE = [
    "dog", "cat", "pet", "puppy", "kitten", "canine", "feline",
    "treat", "chew", "kibble",
]

# Out-of-scope markers for the broad filter (livestock, birds, medicines, etc.)
BROAD_EXCLUDE = [
    "bird food", "wild bird", "poultry feed", "chicken feed",
    "swine", "cattle", "horse feed", "equine", "livestock",
    "reptile", "parrot", "fish food", "aquatic",
    "rabbit feed", "goat", "sheep", "bovine",
    "injectable", "injection", "vaccine", "drug", "pharmaceutical",
    "medical device",
]


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _lower(row: dict, *fields: str) -> str:
    """Concatenate and lowercase the values of the given fields."""
    return " ".join(row.get(f, "") or "" for f in fields).lower()


def is_strict_candidate(text: str) -> bool:
    """True if text passes the strict pet-food inclusion check."""
    t = text.lower()
    if any(ex in t for ex in STRICT_EXCLUDE):
        return False
    return any(inc in t for inc in STRICT_INCLUDE)


def strict_candidate_reason(text: str) -> tuple[bool, str]:
    """Return strict candidate status plus the first matching include/exclude reason."""
    t = text.lower()
    excluded = next((ex for ex in STRICT_EXCLUDE if ex in t), None)
    if excluded:
        return False, f"excluded: '{excluded}'"
    included = next((inc for inc in STRICT_INCLUDE if inc in t), None)
    if included:
        return True, f"matched: '{included}'"
    return False, "no strict pet-food phrase"


def is_broad_in_scope(text: str) -> tuple[bool, str]:
    """Return (in_scope, reason) using the broad companion-animal filter."""
    t = text.lower()
    neg_hit = next((n for n in BROAD_EXCLUDE if n in t), None)
    if neg_hit:
        return False, f"excluded: '{neg_hit}'"
    pos_hit = next((p for p in BROAD_INCLUDE if p in t), None)
    if pos_hit:
        return True, f"matched: '{pos_hit}'"
    return False, "no match"


# ---------------------------------------------------------------------------
# CSV loader
# ---------------------------------------------------------------------------

def load_csv(path: str, encoding: str = "utf-8") -> list[dict]:
    """Load a CSV file into a list of dicts.  Returns [] if file missing."""
    if not os.path.exists(path):
        print(f"  WARNING: file not found — {path}", file=sys.stderr)
        return []
    with open(path, newline="", encoding=encoding) as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Missing-value analysis
# ---------------------------------------------------------------------------

def missing_values(rows: list[dict], fields: list[str]) -> dict[str, dict]:
    """Return per-field missing-value counts and percentages."""
    n = len(rows)
    result = {}
    for field in fields:
        empty = sum(1 for r in rows if not (r.get(field) or "").strip())
        result[field] = {
            "missing": empty,
            "present": n - empty,
            "pct_missing": round(100 * empty / n, 1) if n else 0,
        }
    return result


# ---------------------------------------------------------------------------
# Per-source inspection functions
# ---------------------------------------------------------------------------

def inspect_fda_cvm(rows: list[dict]) -> dict[str, Any]:
    """
    FDA CVM covers all animal/vet recalls.
    Apply the broad companion-animal filter and classify each row as:
      candidate  — matches broad include, no broad exclude
      excluded   — matches a broad exclude term
      borderline — matches neither (hedgehog food, pig ears, medicines, etc.)
    """
    text_fields = ["Product-Description", "Recall-Reason-Description", "Brand-Names"]
    candidates, excluded, borderline = [], [], []

    for r in rows:
        combined = _lower(r, *text_fields)
        in_scope, reason = is_broad_in_scope(combined)
        r["_scope_reason"] = reason
        neg_hit = next((n for n in BROAD_EXCLUDE if n in combined), None)
        if neg_hit:
            excluded.append(r)
        elif in_scope:
            candidates.append(r)
        else:
            borderline.append(r)

    key_fields = ["Product-Description", "Recall-Reason-Description", "Brand-Names",
                  "Date", "Terminated-Recall"]

    return {
        "source": "FDA CVM Animal & Veterinary Recalls",
        "file": "fda_animal_veterinary_recalls.csv",
        "total_rows": len(rows),
        "candidate_count": len(candidates),
        "excluded_count": len(excluded),
        "borderline_count": len(borderline),
        "candidate_method": "broad companion-animal filter (FDA CVM is already animal/vet scoped)",
        "missing_values": missing_values(rows, key_fields),
        "candidate_examples": [
            {k: r.get(k, "") for k in key_fields}
            for r in candidates[:10]
        ],
        "rejected_examples": [
            {k: r.get(k, ""), "_scope_reason": r.get("_scope_reason", "")}
            for k in key_fields
            for r in (excluded + borderline)[:10]
        ][:10],
        "notes": (
            f"{len(candidates)} rows match companion-animal terms (dog/cat/pet/puppy/kitten). "
            f"{len(excluded)} rows clearly excluded (livestock, birds, medicines). "
            f"{len(borderline)} rows borderline (pig ears, hedgehog food, etc.) — "
            "will be reviewed manually in Phase 3."
        ),
    }


def inspect_rasff(rows: list[dict]) -> dict[str, Any]:
    """
    RASFF export is already pre-filtered to category='pet food'.
    Report classification breakdown and hazard types.
    """
    text_fields = ["subject", "hazards", "classification", "notifying_country",
                   "reference", "date", "risk_decision", "origin"]
    key_fields  = ["reference", "subject", "date", "classification",
                   "risk_decision", "hazards", "notifying_country", "origin"]

    classifications: dict[str, int] = {}
    for r in rows:
        c = (r.get("classification") or "").strip()
        classifications[c] = classifications.get(c, 0) + 1

    # All rows are candidates — source was manually filtered to pet food
    return {
        "source": "EU RASFF Manual Export",
        "file": "eu_rasff_pet_food_raw.csv",
        "total_rows": len(rows),
        "candidate_count": len(rows),
        "excluded_count": 0,
        "borderline_count": 0,
        "candidate_method": "all rows in scope — source pre-filtered to category=pet food",
        "classification_breakdown": classifications,
        "missing_values": missing_values(rows, text_fields),
        "candidate_examples": [
            {k: r.get(k, "") for k in key_fields}
            for r in rows[:10]
        ],
        "rejected_examples": [],
        "notes": (
            "All 60 rows have category='pet food'. "
            f"Classification breakdown: {classifications}. "
            "No exclusion needed; all rows pass to Phase 3 review."
        ),
    }


def inspect_uk_fsa(rows: list[dict]) -> dict[str, Any]:
    """
    UK FSA covers all food alerts (human + pet + feed).
    Apply strict inclusion terms on title + productDetails fields.
    """
    text_fields = ["title", "productDetails", "problem", "notation",
                   "created", "alertURL", "reportingBusiness"]
    candidates, rejected = [], []

    for r in rows:
        combined = _lower(r, "title", "productDetails")
        if is_strict_candidate(combined):
            candidates.append(r)
        else:
            rejected.append(r)

    return {
        "source": "UK Food Standards Agency Food Alerts",
        "file": "uk_fsa_food_alerts_raw.csv",
        "total_rows": len(rows),
        "candidate_count": len(candidates),
        "excluded_count": len(rejected),
        "borderline_count": 0,
        "candidate_method": "strict inclusion terms on title + productDetails",
        "missing_values": missing_values(rows, text_fields),
        "candidate_examples": [
            {k: r.get(k, "") for k in ["notation", "title", "created", "problem", "alertURL"]}
            for r in candidates[:10]
        ],
        "rejected_examples": [
            {k: r.get(k, "") for k in ["notation", "title"]}
            for r in rejected[:10]
        ],
        "notes": (
            f"{len(candidates)} of {len(rows)} rows match strict pet-food inclusion terms. "
            f"{len(rejected)} rows are human food or non-pet alerts (expected — source is unfiltered). "
            "Strict filter used because source contains mostly human food."
        ),
    }


def inspect_openfda(rows: list[dict]) -> dict[str, Any]:
    """
    openFDA Food Enforcement records were collected via broad keyword queries.
    Apply strict inclusion terms on product_description + reason_for_recall.
    """
    text_fields = ["product_description", "reason_for_recall", "recalling_firm",
                   "recall_number", "recall_initiation_date", "product_type",
                   "_query_term"]
    candidates, rejected = [], []

    for r in rows:
        combined = _lower(r, "product_description", "reason_for_recall")
        if is_strict_candidate(combined):
            candidates.append(r)
        else:
            rejected.append(r)

    # Query-term breakdown
    query_counts: dict[str, int] = {}
    for r in rows:
        q = r.get("_query_term", "unknown")
        query_counts[q] = query_counts.get(q, 0) + 1

    return {
        "source": "openFDA Food Enforcement API (multi-keyword)",
        "file": "openfda_pet_food_enforcement_raw.csv",
        "total_rows": len(rows),
        "candidate_count": len(candidates),
        "excluded_count": len(rejected),
        "borderline_count": 0,
        "candidate_method": "strict inclusion terms on product_description + reason_for_recall",
        "query_term_breakdown": query_counts,
        "missing_values": missing_values(rows, text_fields),
        "candidate_examples": [
            {k: r.get(k, "") for k in
             ["product_description", "reason_for_recall", "recalling_firm",
              "recall_initiation_date", "_query_term"]}
            for r in candidates[:10]
        ],
        "rejected_examples": [
            {k: r.get(k, "") for k in ["product_description", "_query_term"]}
            for r in rejected[:10]
        ],
        "notes": (
            f"Only {len(candidates)} of {len(rows)} raw records pass strict filter. "
            "Most records are human food (e.g. 'hot dog buns') triggered by broad keyword queries. "
            "openFDA is confirmed a poor source for this project; "
            "FDA CVM XLSX should be used as the primary US source."
        ),
    }


def inspect_canada_cfia(rows: list[dict]) -> dict[str, Any]:
    """
    Canada recalls include CFIA food/feed rows and Consumer Product Safety rows.
    Apply strict Phase 2 pet-food inclusion/exclusion terms on recall text fields.
    """
    text_fields = ["Title", "Product", "Issue", "Category", "Organization",
                   "Recall class", "Last updated", "URL"]
    candidates, rejected = [], []

    for r in rows:
        combined = _lower(r, "Title", "Product", "Issue", "Category")
        is_candidate, reason = strict_candidate_reason(combined)
        r["_scope_reason"] = reason
        if is_candidate:
            candidates.append(r)
        else:
            rejected.append(r)

    org_counts: dict[str, int] = {}
    for r in candidates:
        org = (r.get("Organization") or "unknown").strip() or "unknown"
        org_counts[org] = org_counts.get(org, 0) + 1

    return {
        "source": "Canada CFIA + Consumer Product Safety recalls",
        "file": "canada_cfia_recalls_raw.csv",
        "total_rows": len(rows),
        "candidate_count": len(candidates),
        "excluded_count": len(rejected),
        "borderline_count": 0,
        "candidate_method": "strict inclusion terms on Title + Product + Issue + Category",
        "organization_candidate_breakdown": org_counts,
        "missing_values": missing_values(rows, text_fields),
        "candidate_examples": [
            {k: r.get(k, "") for k in
             ["Title", "Product", "Issue", "Category", "Organization",
              "Recall class", "Last updated", "URL", "_scope_reason"]}
            for r in candidates[:10]
        ],
        "rejected_examples": [
            {k: r.get(k, "") for k in
             ["Title", "Product", "Issue", "Category", "Organization",
              "Last updated", "_scope_reason"]}
            for r in rejected[:10]
        ],
        "notes": (
            f"{len(candidates)} of {len(rows)} Canada CFIA/CPS records match strict "
            "pet-food inclusion terms. The saved Canada raw file is intentionally broad "
            "(CFIA food/feed plus Consumer Product Safety), so most rows are expected "
            "to be human food or non-pet consumer-product recalls."
        ),
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_inspection_summary(
    results: dict[str, dict],
    output_dir: str,
    timestamp: str,
) -> str:
    """Write data/interim/inspection_summary.json."""
    total_raw = sum(r["total_rows"] for r in results.values())
    total_candidates = sum(r["candidate_count"] for r in results.values())

    summary = {
        "inspection_timestamp": timestamp,
        "sources": results,
        "overall": {
            "total_raw_rows": total_raw,
            "total_candidates_across_sources": total_candidates,
            "note": (
                "Candidates are not deduplicated across sources. "
                "Deduplication and final filtering happen in Phase 3."
            ),
        },
    }

    path = os.path.join(output_dir, "inspection_summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"  Written → {path}")
    return path


def write_candidate_counts(results: dict[str, dict], output_dir: str) -> str:
    """Write data/interim/source_candidate_counts.csv."""
    path = os.path.join(output_dir, "source_candidate_counts.csv")
    fieldnames = [
        "source_name", "file", "total_rows",
        "candidate_count", "candidate_method",
        "excluded_count", "borderline_count", "notes",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for key, r in results.items():
            writer.writerow({
                "source_name":      r["source"],
                "file":             r["file"],
                "total_rows":       r["total_rows"],
                "candidate_count":  r["candidate_count"],
                "candidate_method": r["candidate_method"],
                "excluded_count":   r["excluded_count"],
                "borderline_count": r.get("borderline_count", 0),
                "notes":            r["notes"],
            })
    print(f"  Written → {path}")
    return path


def write_inspection_notes(
    results: dict[str, dict],
    docs_dir: str,
    timestamp: str,
) -> str:
    """Overwrite docs/data_inspection_notes.md with structured findings."""
    path = os.path.join(docs_dir, "data_inspection_notes.md")

    def _table_row(r: dict, keys: list[str], maxlen: int = 60) -> str:
        vals = [str(r.get(k, ""))[:maxlen].replace("|", "/") for k in keys]
        return "| " + " | ".join(vals) + " |"

    lines = [
        "# Data Inspection Notes",
        "",
        f"*Generated by `src/inspect_data.py` — {timestamp}*",
        "",
        "---",
        "",
        "## Overall Candidate Summary",
        "",
        "| Source | Total rows | Candidates | Method |",
        "|---|---|---|---|",
    ]
    for r in results.values():
        lines.append(
            f"| {r['source']} | {r['total_rows']:,} | "
            f"**{r['candidate_count']}** | {r['candidate_method'][:55]} |"
        )

    total_raw = sum(r["total_rows"] for r in results.values())
    total_cand = sum(r["candidate_count"] for r in results.values())
    lines += [
        f"| **TOTAL** | **{total_raw:,}** | **{total_cand}** | *(not deduplicated)* |",
        "",
        "> Candidates are not deduplicated across sources.",
        "> Deduplication and final scope decisions happen in Phase 3 (clean_data.py).",
        "",
        "---",
        "",
    ]

    # ── per-source sections ──────────────────────────────────────────────
    for key, r in results.items():
        lines += [
            f"## {r['source']}",
            "",
            f"- **File:** `data/raw/{r['file']}`",
            f"- **Total rows:** {r['total_rows']:,}",
            f"- **Candidates:** {r['candidate_count']}",
            f"- **Excluded:** {r['excluded_count']}",
        ]
        if r.get("borderline_count"):
            lines.append(f"- **Borderline:** {r['borderline_count']}")
        lines += [
            f"- **Method:** {r['candidate_method']}",
            "",
            f"**Notes:** {r['notes']}",
            "",
        ]

        # Missing values (compact)
        mv = r.get("missing_values", {})
        if mv:
            lines += ["**Missing values:**", ""]
            lines += ["| Field | Missing | % |", "|---|---|---|"]
            for field, stats in mv.items():
                if stats["missing"] > 0:
                    lines.append(f"| `{field}` | {stats['missing']} | {stats['pct_missing']}% |")
            lines.append("")

        # Special breakdowns
        if "classification_breakdown" in r:
            lines += ["**Classification breakdown (RASFF):**", ""]
            lines += ["| Classification | Count |", "|---|---|"]
            for cls, cnt in sorted(r["classification_breakdown"].items()):
                lines.append(f"| {cls} | {cnt} |")
            lines.append("")

        if "query_term_breakdown" in r:
            lines += ["**openFDA query-term breakdown:**", ""]
            lines += ["| Query term | Rows fetched |", "|---|---|"]
            for term, cnt in sorted(r["query_term_breakdown"].items()):
                lines.append(f"| `{term}` | {cnt} |")
            lines.append("")

        if "organization_candidate_breakdown" in r:
            lines += ["**Candidate organization breakdown:**", ""]
            lines += ["| Organization | Candidates |", "|---|---|"]
            for org, cnt in sorted(r["organization_candidate_breakdown"].items()):
                lines.append(f"| {org} | {cnt} |")
            lines.append("")

        # Candidate examples
        cex = r.get("candidate_examples", [])
        if cex:
            lines += [f"### Example candidate rows (up to 10)", ""]
            for i, ex in enumerate(cex[:10], 1):
                # Find the most informative single-line representation
                desc = (
                    ex.get("Product-Description")
                    or ex.get("subject")
                    or ex.get("title")
                    or ex.get("Title")
                    or ex.get("product_description")
                    or ex.get("Product")
                    or ""
                )
                reason = (
                    ex.get("Recall-Reason-Description")
                    or ex.get("hazards")
                    or ex.get("problem")
                    or ex.get("reason_for_recall")
                    or ex.get("Issue")
                    or ""
                )
                date = (
                    ex.get("Date") or ex.get("date") or ex.get("created") or
                    ex.get("recall_initiation_date") or ex.get("Last updated") or ""
                )
                lines.append(
                    f"{i}. **{desc[:80]}**"
                    + (f"  \n   _{reason[:100]}_" if reason else "")
                    + (f"  \n   ({date[:20]})" if date else "")
                )
            lines.append("")

        # Rejected examples
        rex = r.get("rejected_examples", [])
        if rex:
            lines += [f"### Example rejected / out-of-scope rows (up to 10)", ""]
            for i, ex in enumerate(rex[:10], 1):
                desc = (
                    ex.get("Product-Description")
                    or ex.get("title")
                    or ex.get("Title")
                    or ex.get("product_description")
                    or ex.get("Product")
                    or str(ex)[:80]
                )
                reason = ex.get("_scope_reason", "")
                lines.append(
                    f"{i}. {desc[:80]}"
                    + (f"  — *{reason}*" if reason else "")
                )
            lines.append("")

        lines += ["---", ""]

    fda = results.get("fda_cvm", {})
    rasff = results.get("rasff", {})
    uk_fsa = results.get("uk_fsa", {})
    openfda = results.get("openfda", {})
    canada = results.get("canada", {})

    lines += [
        "## Decisions and Next Steps",
        "",
        f"- **FDA CVM**: Treat the broad candidate set ({fda.get('candidate_count', 0)}) as Phase 3 inspection input;",
        f"  review {fda.get('borderline_count', 0)} borderline rows manually.",
        f"- **RASFF**: All {rasff.get('candidate_count', 0)} rows remain inspection candidates because the export is pre-filtered to pet food.",
        f"- **UK FSA**: {uk_fsa.get('candidate_count', 0)} strict candidates remain; rejected rows are mostly human-food alerts.",
        f"- **openFDA**: {openfda.get('candidate_count', 0)} row(s) pass strict filter. Source remains noisy and low-value.",
        f"- **Canada CFIA/CPS**: {canada.get('candidate_count', 0)} strict candidates remain for Phase 3 review; rejected rows are",
        "  mostly human food or non-pet consumer-product recalls.",
        f"- **Total likely inspection candidate pool**: {total_cand} rows before deduplication and manual review.",
        "  This is below the 200-row minimum target, so Phase 3 should preserve source-review notes",
        "  and avoid treating these inspection counts as final dataset counts.",
        "",
        "---",
        "",
        "*End of inspection notes.*",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Written → {path}")
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 2 / 2.6: Inspect all raw sources and estimate pet-food candidate counts.\n\n"
            "Does NOT modify raw files. Writes inspection outputs only.\n\n"
            "Outputs:\n"
            "  data/interim/inspection_summary.json\n"
            "  data/interim/source_candidate_counts.csv\n"
            "  docs/data_inspection_notes.md"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        default="data/raw/",
        help="Directory containing raw files (default: data/raw/)",
    )
    parser.add_argument(
        "--output",
        default="data/interim/",
        help="Directory to save inspection outputs (default: data/interim/)",
    )
    parser.add_argument(
        "--docs",
        default="docs/",
        help="Directory containing documentation markdown files (default: docs/)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[inspect_data] Starting inspection — {timestamp}")

    # ── load raw files ──────────────────────────────────────────────────────
    fda_rows   = load_csv(os.path.join(args.input, "fda_animal_veterinary_recalls.csv"))
    rasff_rows = load_csv(os.path.join(args.input, "eu_rasff_pet_food_raw.csv"),
                          encoding="utf-8-sig")
    fsa_rows   = load_csv(os.path.join(args.input, "uk_fsa_food_alerts_raw.csv"))
    of_rows    = load_csv(os.path.join(args.input, "openfda_pet_food_enforcement_raw.csv"))
    ca_rows    = load_csv(os.path.join(args.input, "canada_cfia_recalls_raw.csv"))

    print(f"\n  Loaded:")
    print(f"    FDA CVM : {len(fda_rows):>5} rows")
    print(f"    RASFF   : {len(rasff_rows):>5} rows")
    print(f"    UK FSA  : {len(fsa_rows):>5} rows")
    print(f"    openFDA : {len(of_rows):>5} rows")
    print(f"    Canada  : {len(ca_rows):>5} rows")

    # ── inspect each source ─────────────────────────────────────────────────
    print("\n  Inspecting sources…")
    results = {
        "fda_cvm":  inspect_fda_cvm(fda_rows),
        "rasff":    inspect_rasff(rasff_rows),
        "uk_fsa":   inspect_uk_fsa(fsa_rows),
        "openfda":  inspect_openfda(of_rows),
        "canada":   inspect_canada_cfia(ca_rows),
    }

    # ── write outputs ────────────────────────────────────────────────────────
    print("\n  Writing outputs…")
    write_inspection_summary(results, args.output, timestamp)
    write_candidate_counts(results, args.output)
    write_inspection_notes(results, args.docs, timestamp)

    # ── terminal summary ─────────────────────────────────────────────────────
    total_raw  = sum(r["total_rows"]      for r in results.values())
    total_cand = sum(r["candidate_count"] for r in results.values())

    print("\n" + "=" * 66)
    print("INSPECTION SUMMARY")
    print("=" * 66)
    print(f"  {'Source':<35} {'Total':>7}  {'Candidates':>11}  {'Method'}")
    print(f"  {'-'*35}  {'-'*7}  {'-'*11}  {'-'*20}")
    for r in results.values():
        print(
            f"  {r['source']:<35} {r['total_rows']:>7}  "
            f"{r['candidate_count']:>11}  "
            f"{r['candidate_method'][:28]}"
        )
    print(f"  {'─'*62}")
    print(f"  {'TOTAL (not deduplicated)':<35} {total_raw:>7}  {total_cand:>11}")
    print("=" * 66)
    print(f"  inspection_summary.json     → {args.output}")
    print(f"  source_candidate_counts.csv → {args.output}")
    print(f"  data_inspection_notes.md    → {args.docs}")
    print("=" * 66)
    print("  Phase 3 (clean_data.py) will apply final scope filtering.")
    print("=" * 66)


if __name__ == "__main__":
    main()
