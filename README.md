# Pet Food Recall Risk Classification with Transformer Embeddings

A supervised multi-label text classification project for classifying pet food recall and safety-alert texts into risk categories.

This project was built as an academic assignment for the Information Retrieval course. It uses official public recall/safety-alert records, frozen transformer sentence embeddings, and sklearn-based multi-label classifiers.

---

## Current Project Status

Completed through:

```text
Phase 11 — Hugging Face Model Preparation (local)
```

Implemented so far:

- Multi-source raw data collection
- Data inspection
- Strict pet-food scope filtering
- Rule-based label mapping
- Label consolidation for small-data modeling
- Final dataset construction
- Train/validation/test split
- Frozen transformer embedding generation
- Multi-label classifier training
- Final held-out test evaluation
- Prediction script (`src/predict.py`)
- Hugging Face dataset files prepared locally (`hf_dataset/`)
- Hugging Face model files prepared locally (`hf_model/`)

Not completed yet:

- Hugging Face dataset upload
- Hugging Face model upload
- Hugging Face Space / Gradio deployment
- Final 2-page assignment report

### Hugging Face dataset files (local, not yet uploaded)

The `hf_dataset/` folder contains the dataset card and split CSVs ready for
upload to a Hugging Face Dataset repository:

```text
hf_dataset/
├── README.md          # HF dataset card (YAML front matter + documentation)
├── train.csv          # 73 rows
├── validation.csv     # 15 rows
└── test.csv           # 15 rows
```

Files are copies of `data/processed/{train,validation,test}.csv` and have not
been modified.

### Hugging Face model files (local, not yet uploaded)

The `hf_model/` folder contains the model card and classifier artifacts ready
for upload to a Hugging Face Model repository:

```text
hf_model/
├── README.md              # HF model card (YAML front matter + documentation)
├── classifier.joblib      # Trained OneVsRestClassifier(LogisticRegression)
├── thresholds.json        # Per-label prediction thresholds (validation-tuned)
├── label_columns.json     # Ordered output label names
├── model_config.json      # Training provenance and selection metadata
├── test_metrics.json      # Final held-out test metrics
└── per_label_metrics.csv  # Per-label precision / recall / F1 on test set
```

The frozen transformer encoder (`sentence-transformers/all-MiniLM-L6-v2`) is
not included — it is loaded at inference time via the `sentence-transformers`
library.

---

## Assignment Goal Alignment

The assignment requires a system that includes:

- a custom dataset
- embeddings
- a trained classifier
- a working Hugging Face demo
- evaluation using training and test data
- several classifiers for higher-grade work

This project addresses those requirements as follows:

| Assignment requirement | Project implementation |
|---|---|
| Specific domain | Pet food recall and safety-alert risk classification |
| Custom dataset | Created from official public recall/safety-alert sources |
| Embeddings | Frozen SentenceTransformer embeddings |
| Trained classifier | Multi-label classifiers trained on transformer embeddings |
| Several classifiers | Dummy baseline, Logistic Regression, Linear SVM, Random Forest |
| Evaluation | Validation comparison and held-out test evaluation |
| Demo | Planned Gradio app on Hugging Face Spaces |

---

## Task Definition

### Task Type

```text
Supervised multi-label text classification
```

The system predicts one or more risk categories for a pet food recall or safety-alert text.

Multi-label means that a record may have:

- one label, if only one risk type is present
- multiple labels, if several risks are described

It does **not** force every example to have multiple labels.

---

## Input Format

Each input text is constructed from brand, product description, and recall/safety reason.

```text
Brand: {brand_names}. Product: {product_description}. Recall reason: {recall_reason_description}.
```

Example:

```text
Brand: Example Brand. Product: Dry dog food. Recall reason: May be contaminated with Salmonella.
```

---

## Output Labels

The final modeling labels are consolidated into three risk categories:

| Final label | Description |
|---|---|
| `PATHOGEN_CONTAMINATION` | Bacterial or pathogen-related contamination, such as Salmonella or Listeria |
| `CHEMICAL_OR_NUTRITIONAL_RISK` | Chemical, toxin, vitamin, mineral, or nutrient-level risks |
| `PHYSICAL_OR_QUALITY_ISSUE` | Foreign material, labeling, packaging, manufacturing, or process-control issues |

The original detailed taxonomy contained six labels:

- `PATHOGEN_CONTAMINATION`
- `MYCOTOXIN_OR_CHEMICAL_CONTAMINATION`
- `NUTRITIONAL_IMBALANCE_OR_TOXICITY`
- `FOREIGN_MATERIAL_CONTAMINATION`
- `LABELING_OR_UNDECLARED_INGREDIENT_ISSUE`
- `QUALITY_OR_PROCESS_CONTROL_ISSUE`

However, the official pet-food recall dataset was small. Several detailed labels had too few positive examples, so the labels were consolidated into the final three-label taxonomy above.

---

## Scope

### Included

- Pet food
- Dog food
- Cat food
- Pet treats
- Pet chews
- Feed for dogs
- Feed for cats

### Excluded

- Human food recalls
- Livestock feed
- Animal drugs
- Veterinary medicines
- General animal products
- Pet illness diagnosis
- Veterinary advice
- Product safety certification

---

## Data Sources

This project uses official public recall and safety-alert sources.

### Sources collected or inspected

| Source | Status |
|---|---|
| FDA Animal & Veterinary Recalls / Withdrawals | Used as a high-relevance official source |
| EU RASFF public export | Used; manually exported from public RASFF Window search results |
| UK FSA Food Alerts | Used as a broad official source, then strictly filtered |
| Canada CFIA / Consumer Product Safety recalls | Used as a broad official source, then strictly filtered |
| openFDA Food Enforcement API | Collected as raw candidate data but found to be noisy for this pet-food scope |
| Data.gov legacy FDA pet food recalls file | Documented but unavailable |
| Other official sources | Documented when inaccessible or unsuitable |

### Data-size decision

The original target was at least 200 final rows. After official source expansion and strict filtering, the available pet-food-specific data remained limited.

The project therefore accepts a small-data limitation:

```text
Final labeled dataset: 103 rows
Uncertain rows excluded: 14
```

This limitation is documented because official pet-food recall records are relatively sparse.

---

## Dataset Creation Process

The dataset was created through the following process:

1. Collect raw recall/safety-alert records from official sources.
2. Inspect each source for pet-food relevance.
3. Apply strict pet-food scope filtering.
4. Normalize source-specific fields into common columns.
5. Apply rule-based initial label mapping.
6. Separate uncertain records from labeled records.
7. Consolidate sparse detailed labels into three final labels.
8. Build the final train/validation/test dataset.

The final dataset excludes uncertain records and uses only records with at least one final risk label.

---

## Final Dataset Summary

Final labeled records:

```text
103
```

Uncertain records excluded:

```text
14
```

Final label positive counts:

| Label | Positive count |
|---|---:|
| `PATHOGEN_CONTAMINATION` | 60 |
| `CHEMICAL_OR_NUTRITIONAL_RISK` | 20 |
| `PHYSICAL_OR_QUALITY_ISSUE` | 26 |

Rows with multiple final labels:

```text
3
```

---

## Train / Validation / Test Split

The dataset was split into train, validation, and test sets.

Because the dataset is small and multi-label, multiple random seeds were searched to avoid validation or test splits with missing labels.

Selected split seed:

```text
557
```

Split summary:

| Split | Rows | PATHOGEN | CHEM/NUTR | PHYS/QUALITY | Multi-label rows |
|---|---:|---:|---:|---:|---:|
| Train | 73 | 44 | 12 | 18 | 1 |
| Validation | 15 | 8 | 4 | 4 | 1 |
| Test | 15 | 8 | 4 | 4 | 1 |

---

## Embedding Model

The project uses frozen transformer sentence embeddings:

```text
sentence-transformers/all-MiniLM-L6-v2
```

The transformer model is **not fine-tuned**.

The pipeline is:

```text
Recall text
→ frozen SentenceTransformer encoder
→ fixed-size sentence embedding
→ sklearn multi-label classifier
→ predicted risk labels
```

Generated embedding shapes:

| Split | Shape |
|---|---:|
| Train | `(73, 384)` |
| Validation | `(15, 384)` |
| Test | `(15, 384)` |

---

## Classifiers

The same saved transformer embeddings were used to train and compare several classifiers:

- Dummy baseline
- `OneVsRestClassifier(LogisticRegression)`
- `OneVsRestClassifier(LinearSVC)`
- `OneVsRestClassifier(RandomForestClassifier)`

The selected model after validation was:

```text
OneVsRestClassifier(LogisticRegression)
```

Validation-selected thresholds:

| Label | Threshold |
|---|---:|
| `PATHOGEN_CONTAMINATION` | 0.50 |
| `CHEMICAL_OR_NUTRITIONAL_RISK` | 0.50 |
| `PHYSICAL_OR_QUALITY_ISSUE` | 0.40 |

---

## Validation Results

Validation set size:

```text
15 examples
```

| Model | Micro F1 | Macro F1 | Weighted F1 | Hamming Loss | Subset Accuracy |
|---|---:|---:|---:|---:|---:|
| Dummy baseline | 0.516 | 0.232 | 0.348 | 0.333 | 0.467 |
| Logistic Regression | 0.941 | 0.933 | 0.950 | 0.044 | 0.867 |
| Linear SVM | 0.903 | 0.857 | 0.893 | 0.067 | 0.800 |
| Random Forest | 0.941 | 0.933 | 0.950 | 0.044 | 0.867 |

Logistic Regression was selected because it achieved the best validation performance while also supporting probability scores and per-label thresholding.

---

## Final Test Results

The selected Logistic Regression model was evaluated once on the held-out test set.

Test set size:

```text
15 examples
```

Overall test metrics:

| Metric | Result |
|---|---:|
| Micro F1 | 0.875 |
| Macro F1 | 0.841 |
| Weighted F1 | 0.881 |
| Hamming Loss | 0.089 |
| Subset Accuracy | 0.800 |

Per-label F1:

| Label | F1 |
|---|---:|
| `PATHOGEN_CONTAMINATION` | 1.000 |
| `CHEMICAL_OR_NUTRITIONAL_RISK` | 0.857 |
| `PHYSICAL_OR_QUALITY_ISSUE` | 0.667 |

The model performed best on pathogen contamination records. The physical or quality issue label was more difficult, likely because it combines several heterogeneous risk types such as foreign material, labeling, packaging, and process-control issues.

Because the dataset and test set are small, these results should be interpreted cautiously.

---

## Repository Structure

```text
pet-food-recall-risk-classification/
├── README.md
├── requirements.txt
├── .gitignore
│
├── data/
│   ├── raw/            # Raw downloaded/exported source files
│   ├── interim/        # Filtered and intermediate files
│   ├── processed/      # Final processed dataset splits
│   └── embeddings/     # Precomputed sentence embeddings
│
├── src/
│   ├── config.py
│   ├── collect_data.py
│   ├── inspect_data.py
│   ├── clean_data.py
│   ├── label_mapping.py
│   ├── build_dataset.py
│   ├── build_embeddings.py
│   ├── train_classifiers.py
│   ├── evaluate.py
│   └── predict.py
│
├── models/
│   ├── classifiers/
│   └── selected/
│
├── results/
│   ├── validation_metrics_summary.csv
│   ├── validation_per_label_metrics.csv
│   ├── test_metrics.json
│   ├── per_label_metrics.csv
│   ├── classification_report.json
│   └── multilabel_confusion_matrices.json
│
├── app/
│   ├── app.py
│   ├── requirements.txt
│   └── README.md
│
├── docs/
│   ├── dataset_creation.md
│   ├── label_guidelines.md
│   ├── data_inspection_notes.md
│   ├── error_analysis.md
│   └── ai_reflection_notes.md
│
└── report/
    └── assignment_report.md
```

---

## Setup

```bash
git clone https://github.com/<your-username>/pet-food-recall-risk-classification.git
cd pet-food-recall-risk-classification

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

For Windows:

```bash
.venv\Scripts\activate
```

---

## Workflow

### Phase 1 — Collect raw data

```bash
python src/collect_data.py --output data/raw/
```

### Phase 2 — Inspect raw sources

```bash
python src/inspect_data.py --input data/raw/ --output data/interim/ --docs docs/
```

### Phase 3 — Clean and scope-filter records

```bash
python src/clean_data.py --input data/raw/ --output data/interim/ --counts data/interim/source_candidate_counts.csv
```

### Phase 4 — Apply detailed rule-based label mapping

```bash
python src/label_mapping.py --input data/interim/filtered_recalls.csv --output data/interim/
```

### Phase 4.5 — Consolidate sparse detailed labels

```bash
python src/label_mapping.py \
  --mode consolidate \
  --input data/interim/auto_labeled_recalls.csv \
  --uncertain data/interim/uncertain_recalls.csv \
  --output data/interim/
```

### Phase 5 — Build final dataset splits

```bash
python src/build_dataset.py \
  --input data/interim/consolidated_labeled_recalls.csv \
  --summary-input data/interim/consolidated_label_summary.json \
  --output data/processed/ \
  --test-size 0.15 \
  --val-size 0.15
```

### Phase 6 — Generate sentence embeddings

```bash
python src/build_embeddings.py \
  --input data/processed/ \
  --output data/embeddings/
```

### Phase 7 — Train classifiers

```bash
python src/train_classifiers.py \
  --embeddings data/embeddings/ \
  --data data/processed/ \
  --output models/ \
  --results results/
```

### Phase 8 — Evaluate selected model

```bash
python src/evaluate.py \
  --models models/ \
  --embeddings data/embeddings/ \
  --data data/processed/ \
  --output results/
```

### Phase 9 — Prediction script

Planned / in progress.

Example target command:

```bash
python src/predict.py \
  --brand "Example Brand" \
  --product "Dry dog food" \
  --reason "May be contaminated with Salmonella"
```

---

## Hugging Face Deployment Status

Completed:

- Dataset: https://huggingface.co/datasets/ShurongSR/pet-food-recall-risk
- Model: https://huggingface.co/ShurongSR/pet-food-recall-risk-classifier

Pending:

- Hugging Face Space with Gradio demo

---

## Limitations

This project has several important limitations:

1. **Small dataset size**  
   Official pet-food-specific recall records are limited. The final labeled dataset contains 103 records.

2. **Small test set**  
   The test set contains only 15 examples, so evaluation results should be interpreted cautiously.

3. **Rule-based labeling**  
   Labels were created using transparent rule-based mapping and manual review of uncertain cases, not by an official risk taxonomy.

4. **Consolidated labels**  
   The final three labels combine several more specific risk types. This improves trainability but reduces granularity.

5. **Source heterogeneity**  
   Records come from multiple official sources with different formats and terminology.

6. **Not a safety authority tool**  
   The model predicts risk categories from text. It does not determine whether a product is safe.

---

## Educational Disclaimer

This project is for educational purposes only.

It does **not** provide:

- veterinary advice
- legal advice
- product safety certification
- official recall interpretation
- medical or nutritional recommendations

Predictions are generated by a machine learning model trained on historical recall and safety-alert text. They may be incorrect or incomplete.

Always consult official recall notices and qualified professionals for authoritative information about pet food safety.
