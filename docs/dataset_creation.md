# Dataset Creation

Document the full process of assembling the pet food recall dataset used in this project.

---

## 1. Data Sources

### Primary: FDA Animal & Veterinary Recalls / Withdrawals
- URL: https://www.fda.gov/animal-veterinary/safety-health/recalls-withdrawals
- Download URL: XLSX export from the CVM data table (see `src/collect_data.py` for exact URL)
- Format: XLSX (downloaded) → also saved as CSV
- Actual columns: `Date`, `Brand-Names`, `Product-Description`, `Recall-Reason-Description`,
  `Company-Name`, `Terminated-Recall`
- Collection method: Direct HTTP GET with browser User-Agent headers (FDA bot-detection requires this)

**Phase 1 result (collected 2026-05-03):**
- Raw rows collected: **49**
- Saved files: `data/raw/fda_animal_veterinary_recalls.xlsx`, `data/raw/fda_animal_veterinary_recalls.csv`
- Provenance record: `data/raw/source_metadata.json`

### Source 2: Data.gov "FDA Pet Food Recalls" (legacy)
- Page URL: https://catalog.data.gov/dataset/fda-pet-food-recalls
- Attempted download: `https://www.accessdata.fda.gov/scripts/newpetfoodrecalls/PetFoodRecallProductsList2009.xls`
- **Status (Phase 1.5, 2026-05-03): UNAVAILABLE — 404 Not Found.**
  The XLS link listed on Data.gov resolves to a broken URL on accessdata.fda.gov.
  Documented in `data/raw/source_inventory.csv`. No file downloaded.

### Source 3: openFDA Food Enforcement API (multi-keyword)
- URL: https://api.fda.gov/food/enforcement.json
- Format: JSON API (paginated)
- Queries used: `product_description:dog/cat/pet/treat/chew/puppy/kitten`
- **Phase 1.5 result (collected 2026-05-03):**
  - Raw rows collected (deduplicated by event_id/recall_number): **107**
  - Saved file: `data/raw/openfda_pet_food_enforcement_raw.csv`
  - Note: broad keyword queries capture many non-pet-food records (e.g. "hot dog buns").
    Scope filtering applied in Phase 2.

### Source 4: UK FSA Food Alerts (European, Phase 1.6)
- API URL: https://data.food.gov.uk/food-alerts/id.json
- Format: JSON Linked Data API (no authentication required)
- Licence: OGL v3 (UK Open Government Licence)
- Columns: `@id`, `title`, `notation`, `created`, `modified`, `type`, `shortTitle`,
  `status`, `alertURL`, `reportingBusiness`, `problem`, `productDetails`, `country`
- **Phase 1.6 result (collected 2026-05-03):**
  - Raw rows collected: **1,314** (all FSA food alerts, unfiltered)
  - ~22 rows have explicit pet food terms in title/product field
  - Saved file: `data/raw/uk_fsa_food_alerts_raw.csv`
  - Note: dataset covers all FSA alerts (human food, pet food, feed). Scope filtering in Phase 2.

### Source 5: EU RASFF — Manual Export (European, Phase 1.6b)
- Portal: https://webgate.ec.europa.eu/rasff-window/screen/search
- **Phase 1.6 automated status:** ACCESS RESTRICTED (API requires EU Login).
  Backend API endpoints return Angular shell for unauthenticated requests.
- **Phase 1.6b result (registered 2026-05-03): MANUALLY EXPORTED — 60 rows.**
  The public RASFF Window consumer search interface allows manual CSV export
  without authentication. Search filter applied: `category = pet food`.
  - Raw rows: **60** (all `category=pet food`, `type=feed`)
  - Date range covered: 2019-06-17 to 2026-04-02
  - Saved file: `data/raw/eu_rasff_pet_food_raw.csv` (already CSV, no conversion)
  - Columns (14): `reference`, `category`, `type`, `subject`, `date`,
    `notifying_country`, `classification`, `risk_decision`, `distribution`,
    `forAttention`, `forFollowUp`, `operator`, `origin`, `hazards`

### Source 6: German BVL — Bundesamt für Verbraucherschutz (European, Phase 1.6)
- **Status: NO PUBLIC API** — Alerts are HTML-only. Direct file access returns HTTP 303 redirect.
- Documented in `data/raw/source_inventory.csv`.

### Source 7: French ANSES (European, Phase 1.6)
- **Status: NO PUBLIC API** — Alerts are HTML/PDF press releases only.
- Documented in `data/raw/source_inventory.csv`.

### Source 8: Canada CFIA + Consumer Product Safety recalls JSON (Phase 2.5)
- Portal: https://recalls-rappels.canada.ca/en
- Download URL: `https://recalls-rappels.canada.ca/sites/default/files/opendata-donneesouvertes/HCRSAMOpenData.json`
- Format: Static JSON file updated daily (no authentication required)
- Licence: Open Government Licence - Canada v2.0
- Columns (11): `NID`, `Title`, `URL`, `Organization`, `Product`, `Issue`,
  `What you should do`, `Category`, `Recall class`, `Last updated`, `Archived`
- **Phase 2.5 result (collected 2026-05-03):**
  - Total records in JSON: **33,473** (all Canadian government recall categories)
  - Saved records: **10,315** (Organization = "CFIA" or "Consumer product safety")
    - CFIA = Canadian Food Inspection Agency (food, feed, plant safety)
    - Consumer product safety = Health Canada branch; handles pet food recalls
    - Excluded: Transport Canada (vehicles), Medical devices, Drugs
  - Pet food keyword matches in saved subset: ~17 records
  - Saved file: `data/raw/canada_cfia_recalls_raw.csv`
  - Note: Scope filtering to pet-food-only records applied in Phase 2/3.

### Source 9: Australia FSANZ Food Recalls (Phase 2.5)
- **Status: INSUFFICIENT DATA (RSS only)**
  - RSS feed (`https://www.foodstandards.gov.au/food-recalls-rss.xml`) confirmed accessible
    but contains only the 10 most-recent recalls — insufficient for historical analysis.
  - Drupal JSON:API endpoint returns HTTP 404 (disabled).
  - No bulk CSV/JSON historical export found.
- Documented in `data/raw/source_inventory.csv`. No file downloaded.

### Source 10: New Zealand MPI Food Recalls / ACVM (Phase 2.5)
- **Status: BOT PROTECTED (Incapsula)**
  - All requests to `mpi.govt.nz` return Incapsula bot-protection challenge.
  - ACVM recalls page (agricultural compounds, vet medicines, pet food, animal feed)
    similarly inaccessible without a real browser session.
- Documented in `data/raw/source_inventory.csv`. No file downloaded.

### Source 11: Australia ACCC Product Safety Recalls (Phase 2.5)
- **Status: NO PUBLIC API**
  - Drupal site with JSON:API disabled (HTTP 404).
  - Search page returns HTML only; no embedded structured data.
  - No public JSON/CSV export endpoint found.
- Documented in `data/raw/source_inventory.csv`. No file downloaded.

### Phase 2.5 raw source summary (2026-05-03)

| # | Source | Rows | Status | File |
|---|---|---|---|---|
| 1 | FDA CVM XLSX | 49 | Downloaded | `fda_animal_veterinary_recalls.csv` |
| 2 | Data.gov XLS (legacy) | 0 | UNAVAILABLE (404) | — |
| 3 | openFDA multi-keyword | 107 (pre-filter) | Downloaded | `openfda_pet_food_enforcement_raw.csv` |
| 4 | UK FSA Food Alerts | 1,314 (pre-filter) | Downloaded | `uk_fsa_food_alerts_raw.csv` |
| 5 | EU RASFF manual export | **60** | Manually exported | `eu_rasff_pet_food_raw.csv` |
| 6 | German BVL | — | NO PUBLIC API | — |
| 7 | French ANSES | — | NO PUBLIC API | — |
| 8 | Canada CFIA (CFIA + CPS) | **10,315** (pre-filter) | Downloaded | `canada_cfia_recalls_raw.csv` |
| 9 | Australia FSANZ | — | INSUFFICIENT DATA (RSS 10 items) | — |
| 10 | New Zealand MPI | — | BOT PROTECTED (Incapsula) | — |
| 11 | Australia ACCC | — | NO PUBLIC API | — |
| | **Total raw rows** | **11,845** | | |

Full provenance: `data/raw/source_metadata.json` · `data/raw/source_inventory.csv`

---

## 2. Scope Filtering

**Include:**
- Pet food (dog food, cat food, general pet food)
- Pet treats (dog treats, cat treats)
- Pet chews

**Exclude:**
- Animal drugs and veterinary medicines
- Livestock feed (cattle, swine, poultry)
- Human food recalls
- General animal products (non-food)
- Pet illness reports (not recalls)

Filtering strategy after Phase 3: strict keyword matching on source-specific title,
product, category, issue/hazard, and reason fields. Rows are included only when
they contain an explicit pet-food phrase such as `pet food`, `dog food`,
`cat food`, `pet treat`, `dog treat`, `pet chew`, or `food for dogs`.
Obvious false positives (`hot dog`, `hotdog`, `corn dog`, `dogfish`) are rejected.

---

## 3. Cleaning Steps

**Phase 3 result (cleaned 2026-05-03):**

- Implemented in `src/clean_data.py`.
- Loaded all five raw source files: FDA CVM, EU RASFF, UK FSA, openFDA, and Canada CFIA/CPS.
- Applied strict pet-food scope filtering only; no labels, manual annotation,
  model code, synthetic data, or train/validation/test split were created.
- Normalized source-specific fields into common columns:
  `source`, `source_id`, `date`, `brand_names`, `product_description`,
  `recall_reason_description`, `source_url`, `raw_title`, `raw_category`,
  and `raw_issue_or_hazard`.
- Preserved source-specific evidence in `raw_text`, `scope_match`, and
  `dedup_key` to support later label mapping.
- Conservatively deduplicated by `source + source_id` when available;
  otherwise by normalized `product_description + recall_reason_description + date`.
- Saved interim files:
  - `data/interim/filtered_recalls.csv`
  - `data/interim/rejected_scope_rows.csv`
  - `data/interim/cleaning_summary.json`

| Source | Raw rows | Strict candidates | After dedup | Rejected |
|---|---:|---:|---:|---:|
| FDA CVM | 49 | 19 | 19 | 30 |
| EU RASFF | 60 | 60 | 60 | 0 |
| UK FSA | 1,314 | 24 | 24 | 1,290 |
| openFDA | 107 | 1 | 1 | 106 |
| Canada CFIA/CPS | 10,315 | 13 | 13 | 10,302 |
| **Total** | **11,845** | **117** | **117** | **11,728** |

No duplicate rows were removed in Phase 3. The cleaned candidate pool remains
below the original 200-row target; this small-data limitation is accepted and
documented rather than hidden.

---

## 4. Rule-Based Label Mapping

**Phase 4 result (mapped 2026-05-03):**

- Implemented in `src/label_mapping.py`.
- Loaded `data/interim/filtered_recalls.csv` with **117** strictly in-scope
  candidate rows.
- Applied transparent keyword/rule patterns over `recall_reason_description`,
  `raw_title`, `raw_issue_or_hazard`, `product_description`, and `raw_text`.
- Wrote rule-labeled rows to `data/interim/auto_labeled_recalls.csv`.
- Wrote rows needing later review to `data/interim/uncertain_recalls.csv`.
- Wrote counts and rule provenance to `data/interim/label_mapping_summary.json`.
- No manual annotation, model training, embeddings, synthetic data, or
  train/validation/test split were created.

| Metric | Count |
|---|---:|
| Total filtered rows | 117 |
| Auto-labeled rows | 103 |
| Uncertain rows | 14 |
| Rows with multiple labels | 6 |

| Label | Positive count |
|---|---:|
| PATHOGEN_CONTAMINATION | 60 |
| MYCOTOXIN_OR_CHEMICAL_CONTAMINATION | 10 |
| NUTRITIONAL_IMBALANCE_OR_TOXICITY | 12 |
| FOREIGN_MATERIAL_CONTAMINATION | 12 |
| LABELING_OR_UNDECLARED_INGREDIENT_ISSUE | 2 |
| QUALITY_OR_PROCESS_CONTROL_ISSUE | 14 |

Uncertain rows are mainly records with product names, broad safety concerns, or
consumer/regulatory wording but no mappable risk cause. They are kept separate
for later review and are not silently forced into a label.

---

## 5. Label Consolidation

**Phase 4.5 result (consolidated 2026-05-03):**

- Added `FINAL_LABEL_COLUMNS` to `src/config.py`.
- Preserved the original six detailed labels in `data/interim/auto_labeled_recalls.csv`.
- Mapped the six detailed labels into a smaller three-label taxonomy for
  small-data modeling.
- Excluded uncertain rows from the consolidated output.
- Saved:
  - `data/interim/consolidated_labeled_recalls.csv`
  - `data/interim/consolidated_label_summary.json`
- No training, embeddings, synthetic data, or train/validation/test split were created.

Final label mapping:

| Final label | Detailed labels included |
|---|---|
| PATHOGEN_CONTAMINATION | PATHOGEN_CONTAMINATION |
| CHEMICAL_OR_NUTRITIONAL_RISK | MYCOTOXIN_OR_CHEMICAL_CONTAMINATION; NUTRITIONAL_IMBALANCE_OR_TOXICITY |
| PHYSICAL_OR_QUALITY_ISSUE | FOREIGN_MATERIAL_CONTAMINATION; LABELING_OR_UNDECLARED_INGREDIENT_ISSUE; QUALITY_OR_PROCESS_CONTROL_ISSUE |

Phase 4.5 counts:

| Metric | Count |
|---|---:|
| Consolidated labeled rows | 103 |
| Uncertain rows excluded | 14 |
| Rows with multiple final labels | 3 |

| Final label | Positive count |
|---|---:|
| PATHOGEN_CONTAMINATION | 60 |
| CHEMICAL_OR_NUTRITIONAL_RISK | 20 |
| PHYSICAL_OR_QUALITY_ISSUE | 26 |

Consolidation was needed because the detailed six-label taxonomy is too sparse
for this closed-source, small-data setting. The sparse detailed labels remain
available for audit, while the final three labels are better suited for later
modeling.

---

## 6. Input Text Construction

Each row is converted to a single text string using the template:

```
Brand: {brand_names}. Product: {product_description}. Recall reason: {recall_reason_description}.
```

---

## 7. Dataset Statistics

**Phase 5 result (built 2026-05-03):**

- Implemented in `src/build_dataset.py`.
- Loaded `data/interim/consolidated_labeled_recalls.csv`.
- Used only `FINAL_LABEL_COLUMNS` from `src/config.py`.
- Excluded uncertain rows by using only the consolidated labeled input.
- Built Hugging Face-ready CSV columns: `text`, `final_labels`, one multi-hot
  column per final label, source metadata, product fields, and raw evidence fields.
- Constructed `text` with `INPUT_TEXT_TEMPLATE`.
- Created a 70/15/15 train/validation/test split.
- **Phase 5.1 split improvement:** searched seeds **0–999** and selected seed
  **557**, which satisfied the preferred constraint of at least **2 positives**
  for every final label in both validation and test.
- Saved:
  - `data/processed/full_dataset.csv`
  - `data/processed/train.csv`
  - `data/processed/validation.csv`
  - `data/processed/test.csv`
  - `data/processed/label_columns.json`
  - `data/processed/dataset_summary.json`
- No embeddings, model training, evaluation, or synthetic data were created.

| Split | Rows | Rows with multiple final labels |
|---|---:|---:|
| Train | 73 | 1 |
| Validation | 15 | 1 |
| Test | 15 | 1 |
| **Total** | **103** | **3** |

Phase 5.1 selected the satisfying seed with the best label-balance score among
the searched seeds. The processed dataset contents and labels were unchanged;
only row assignment to train/validation/test changed.

---

## 8. Label Distribution

Final-label positive counts by split:

| Label | Count | % of total |
|---|---|---|
| PATHOGEN_CONTAMINATION | 60 | 58.3% |
| CHEMICAL_OR_NUTRITIONAL_RISK | 20 | 19.4% |
| PHYSICAL_OR_QUALITY_ISSUE | 26 | 25.2% |

| Split | PATHOGEN_CONTAMINATION | CHEMICAL_OR_NUTRITIONAL_RISK | PHYSICAL_OR_QUALITY_ISSUE |
|---|---:|---:|---:|
| Train | 44 | 12 | 18 |
| Validation | 8 | 4 | 4 |
| Test | 8 | 4 | 4 |

---

## 9. Embedding Generation

**Phase 6 result (generated 2026-05-03):**

- Implemented in `src/build_embeddings.py`.
- Used frozen `sentence-transformers/all-MiniLM-L6-v2` from `EMBEDDING_MODEL_NAME`.
- Encoded the `text` column from the processed train, validation, and test CSVs.
- Saved:
  - `data/embeddings/train_embeddings.npy`
  - `data/embeddings/validation_embeddings.npy`
  - `data/embeddings/test_embeddings.npy`
  - `data/embeddings/embedding_config.json`
- Validated that each embedding array row count matches its CSV split and that
  all splits have the same embedding dimension.
- No classifier training, model evaluation, label changes, or synthetic data
  were performed.

| Split | Rows | Embedding shape |
|---|---:|---|
| Train | 73 | `(73, 384)` |
| Validation | 15 | `(15, 384)` |
| Test | 15 | `(15, 384)` |

Embedding dimension: **384**.

---

## 10. Classifier Training

**Phase 7 result (trained 2026-05-03):**

- Implemented in `src/train_classifiers.py`.
- Loaded only train and validation embeddings.
- Used `FINAL_LABEL_COLUMNS` from `src/config.py`.
- Trained:
  - Dummy baseline (`OneVsRestClassifier(DummyClassifier)`)
  - `OneVsRestClassifier(LogisticRegression)`
  - `OneVsRestClassifier(LinearSVC)`
  - `OneVsRestClassifier(RandomForestClassifier)`
- Evaluated on the validation split only.
- Tuned per-label thresholds over `0.20–0.80` for models with `predict_proba`.
- Used default binary predictions for `LinearSVC`.
- Saved trained classifiers under `models/classifiers/`.
- Saved validation metrics:
  - `results/validation_metrics_summary.csv`
  - `results/validation_per_label_metrics.csv`
  - `models/classifiers/classifier_metadata.json`
- Selected a provisional best model by validation macro F1.
- Saved provisional selection metadata:
  - `models/selected/model_config.json`
  - `models/selected/thresholds.json`
- The test set was not evaluated.

| Model | Micro F1 | Macro F1 | Weighted F1 | Hamming loss | Subset accuracy |
|---|---:|---:|---:|---:|---:|
| Dummy baseline | 0.516 | 0.232 | 0.348 | 0.333 | 0.467 |
| Logistic regression | 0.941 | 0.933 | 0.950 | 0.044 | 0.867 |
| Linear SVC | 0.903 | 0.857 | 0.893 | 0.067 | 0.800 |
| Random forest | 0.941 | 0.933 | 0.950 | 0.044 | 0.867 |

Provisional selected model: **logistic_regression**.

Selected thresholds:

| Label | Threshold |
|---|---:|
| PATHOGEN_CONTAMINATION | 0.50 |
| CHEMICAL_OR_NUTRITIONAL_RISK | 0.50 |
| PHYSICAL_OR_QUALITY_ISSUE | 0.40 |

Logistic regression and random forest tied on validation macro F1. The
provisional selection is validation-only and must be confirmed in the later
test-evaluation phase.

---

## 11. Final Test Evaluation

**Phase 8 result (evaluated 2026-05-03):**

- Implemented in `src/evaluate.py`.
- Loaded selected model metadata from `models/selected/model_config.json`.
- Loaded validation-selected thresholds from `models/selected/thresholds.json`.
- Evaluated `models/classifiers/logistic_regression.joblib` on the held-out test
  set exactly once.
- Saved:
  - `results/test_metrics.json`
  - `results/per_label_metrics.csv`
  - `results/classification_report.json`
  - `results/multilabel_confusion_matrices.json`
- Updated `docs/error_analysis.md`.
- No training, threshold tuning, model selection changes, embedding regeneration,
  label changes, or synthetic data were performed.

| Metric | Test value |
|---|---:|
| Micro F1 | 0.875 |
| Macro F1 | 0.841 |
| Weighted F1 | 0.881 |
| Hamming loss | 0.089 |
| Subset accuracy | 0.800 |

| Label | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| PATHOGEN_CONTAMINATION | 1.000 | 1.000 | 1.000 | 8 |
| CHEMICAL_OR_NUTRITIONAL_RISK | 1.000 | 0.750 | 0.857 | 4 |
| PHYSICAL_OR_QUALITY_ISSUE | 0.600 | 0.750 | 0.667 | 4 |

The held-out test set contains only 15 rows, so metrics are sensitive to a small
number of examples. Full error notes are in `docs/error_analysis.md`.

---

## 12. Known Limitations

- TODO: list any biases or gaps in the data
- TODO: note date range covered
- TODO: note if any label was dropped due to insufficient examples
