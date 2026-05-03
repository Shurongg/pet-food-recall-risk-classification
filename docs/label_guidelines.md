# Label Guidelines

Annotation guidelines and Phase 4 rule patterns for the six multi-label risk
categories used in this project.

---

## General Rules

- A single record can have multiple labels.
- Assign labels from recall-risk text: `recall_reason_description`, `raw_title`,
  `raw_issue_or_hazard`, `product_description`, and preserved `raw_text`.
- Do not infer labels from product type alone. A pet-food product name without a
  clear risk cause remains uncertain.
- If no rule matches, or the only wording is vague, mark the row uncertain.
- Phase 4 outputs are initial rule-based labels only. They are not manual
  annotations and are not a final train/test dataset.

---

## Phase 4 Output Files

- `data/interim/auto_labeled_recalls.csv`: rows with at least one confident rule match.
- `data/interim/uncertain_recalls.csv`: rows needing later human review.
- `data/interim/label_mapping_summary.json`: counts, rule patterns, and provenance.
- `data/interim/consolidated_labeled_recalls.csv`: Phase 4.5 rows with final
  3-label taxonomy for small-data modeling.
- `data/interim/consolidated_label_summary.json`: Phase 4.5 consolidation counts
  and label mapping provenance.

Both CSVs include a semicolon-separated `labels` column and one multi-hot column
per label in `src/config.py`.

---

## Final 3-Label Taxonomy for Modeling

Phase 4.5 consolidates the original six detailed labels into three final labels
because the strictly filtered dataset is small. Several detailed labels have too
few positives for stable small-data modeling, especially
`LABELING_OR_UNDECLARED_INGREDIENT_ISSUE`. The detailed labels are preserved in
`auto_labeled_recalls.csv` and in `consolidated_labeled_recalls.csv`, but model
building should use `FINAL_LABEL_COLUMNS` from `src/config.py`.

### PATHOGEN_CONTAMINATION

Final label for biological pathogen and microbial hazard recalls.

Detailed labels included:
- `PATHOGEN_CONTAMINATION`

### CHEMICAL_OR_NUTRITIONAL_RISK

Final label for chemical, mycotoxin, additive, residue, nutrient excess, or
nutrient deficiency risks.

Detailed labels included:
- `MYCOTOXIN_OR_CHEMICAL_CONTAMINATION`
- `NUTRITIONAL_IMBALANCE_OR_TOXICITY`

### PHYSICAL_OR_QUALITY_ISSUE

Final label for physical contaminants, labeling/warning issues, packaging,
inspection, hygiene, storage, import, or other process-control failures.

Detailed labels included:
- `FOREIGN_MATERIAL_CONTAMINATION`
- `LABELING_OR_UNDECLARED_INGREDIENT_ISSUE`
- `QUALITY_OR_PROCESS_CONTROL_ISSUE`

Boundary notes:
- Final labels remain multi-label. A row can still be both
  `PATHOGEN_CONTAMINATION` and `PHYSICAL_OR_QUALITY_ISSUE` if both a pathogen
  and a process failure are stated.
- Uncertain rows remain excluded from `consolidated_labeled_recalls.csv`.
- Consolidation is a modeling simplification, not a claim that the detailed
  hazards are equivalent.

Phase 4.5 final label counts:

| Final label | Positive count |
|---|---:|
| PATHOGEN_CONTAMINATION | 60 |
| CHEMICAL_OR_NUTRITIONAL_RISK | 20 |
| PHYSICAL_OR_QUALITY_ISSUE | 26 |

---

## Rule Patterns by Label

### PATHOGEN_CONTAMINATION

Use when text identifies a biological pathogen or microbial hazard.

Rule terms:
- Salmonella, including species/serotypes and `Salmonella spp.`
- Listeria, including `Listeria monocytogenes` and `Listeria spp.`
- E. coli / Escherichia coli
- Enterobacteriaceae
- pathogenic microorganisms
- foodborne illness
- microbial hazard, microbiological
- aerobic mesophiles / mesophiles aerobic
- bird flu / avian influenza
- bacteria, bacterial, bacterium

Boundary notes:
- Generic phrases like `possible contamination` are not enough without a
  pathogen or microbial class.
- `Microbial hazard` is treated as pathogen contamination because it names a
  biological hazard class.

### MYCOTOXIN_OR_CHEMICAL_CONTAMINATION

Use when text identifies a mycotoxin, pesticide, heavy metal, chemical hazard,
drug/residue issue, or unauthorized additive.

Rule terms:
- aflatoxin, mycotoxin, vomitoxin, deoxynivalenol, DON
- pesticide residue, pesticide
- ethylene oxide
- chlorpyrifos
- lead contamination/high content, heavy metals, mercury, cadmium, arsenic
- cannabidiol / CBD
- chemical hazard, chemical contamination
- unauthorized/non-approved feed additive
- feed additive
- drug residue, residue

Boundary notes:
- Standalone `lead` is not used because it can appear as a verb.
- Vitamin/mineral excess can also trigger `NUTRITIONAL_IMBALANCE_OR_TOXICITY`
  when the nutrient itself is the hazard.

### NUTRITIONAL_IMBALANCE_OR_TOXICITY

Use when text identifies excess, deficiency, or unsafe levels of vitamins,
minerals, or nutrients.

Rule terms:
- Vitamin D / D3
- Vitamin A
- thiamine / Vitamin B1
- Vitamin K1
- zinc, copper, iron, calcium, phosphorus, cobalt
- elevated/high/exceeding vitamin levels
- low or insufficient thiamine
- nutrient deficiency

Boundary notes:
- Nutritional labels can co-occur with chemical/additive labels for unauthorized
  mineral or vitamin feed additives.

### FOREIGN_MATERIAL_CONTAMINATION

Use when text identifies a physical object or foreign body in the product.

Rule terms:
- foreign material, foreign body, foreign object, foreign bodies
- sharp pieces
- metal objects/pieces/fragments/particles, pieces of metal, loose metal
- metal fragments
- plastic pieces/fragments or plastic contamination
- glass pieces/fragments
- porcelain pieces
- bone pieces/fragments or large pieces of bone
- sharp foreign body

Boundary notes:
- Physical injury/choking language alone is not enough unless a foreign object
  or physical material is named.

### LABELING_OR_UNDECLARED_INGREDIENT_ISSUE

Use when text identifies missing, incorrect, or incomplete label information.

Rule terms:
- undeclared, not declared, fails to declare
- allergen, allergy, allergic
- mislabeled/mislabelled, labeling/labelling error, incorrect label
- no labeling/labelling
- missing warning on a label
- label/warning combinations

Boundary notes:
- A product name or brand label is not a labeling issue by itself.

### QUALITY_OR_PROCESS_CONTROL_ISSUE

Use when text identifies a manufacturing, storage, inspection, import, packaging,
or process-control failure not covered fully by other labels.

Rule terms:
- insanitary conditions
- storage process/conditions issue
- defective closure, packaging failure, packaging defect
- process deviation, manufacturing defect, GMP
- official controls issue
- veterinary checks issue, including spelling variants in source text
- insufficient checks, skipped checks
- documentary or identity check failures
- illegal/unauthorized import
- not inspected / absence of inspection
- hygiene failure or document failure

Boundary notes:
- General `quality issue`, `safety concern`, or `unsafe` wording remains
  uncertain unless a concrete process failure is named.
- Quality/process labels can co-occur with pathogen labels when the text names
  both contamination and poor storage or insanitary conditions.

---

## Uncertain Cases

Mark a row uncertain when:
- no label rule matches;
- only vague phrases are present, such as `possible contamination`,
  `potential contamination`, `may be contaminated`, `quality issue`,
  `out of an abundance of caution`, or `consumer complaint`;
- regulatory notification text gives severity/status but no mappable hazard.

Examples from Phase 4 uncertain output:
- `Consumer complaint on pet food from Germany`
- `cat food products because of safety concerns`
- pet food recall titles with no stated risk cause

---

## Multi-label Examples

| Recall reason snippet | Labels |
|---|---|
| `Salmonella contamination and insanitary storage conditions` | PATHOGEN_CONTAMINATION; QUALITY_OR_PROCESS_CONTROL_ISSUE |
| `Non authorized feed additive (vit. K1) in pet food` | MYCOTOXIN_OR_CHEMICAL_CONTAMINATION; NUTRITIONAL_IMBALANCE_OR_TOXICITY |
| `Pet food with high number of bacteria, no labeling and defective closure` | PATHOGEN_CONTAMINATION; LABELING_OR_UNDECLARED_INGREDIENT_ISSUE; QUALITY_OR_PROCESS_CONTROL_ISSUE |
| `Large pieces of bone in pet food without warning on the label` | FOREIGN_MATERIAL_CONTAMINATION; LABELING_OR_UNDECLARED_INGREDIENT_ISSUE |
