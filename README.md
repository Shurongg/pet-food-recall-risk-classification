# Pet Food Recall Risk Classification with Transformer Embeddings

A supervised multi-label text classification system for FDA pet food recall descriptions.
Built as an academic assignment for the Information Retrieval course.

---

## Assignment Goal Alignment

This project addresses the task of automatically classifying the **risk type** associated
with pet food recalls, using real-world recall text from FDA records. The pipeline combines
frozen transformer sentence embeddings with traditional sklearn classifiers, making it an
applied NLP + IR project.

---

## Task Definition

**Input:** A short text combining brand name, product description, and recall reason.

**Format:**
```
Brand: {brand_names}. Product: {product_description}. Recall reason: {recall_reason_description}.
```

**Output:** One or more risk labels from the taxonomy below (multi-label classification).

---

## Scope

**Included:**
- Pet food (dog food, cat food)
- Pet treats and pet chews

**Excluded:**
- Animal drugs / veterinary medicines
- Livestock feed
- General animal products
- Human food recalls
- Pet illness diagnoses

---

## Label Taxonomy

| Label | Description |
|---|---|
| `PATHOGEN_CONTAMINATION` | Bacterial or viral contamination (Salmonella, Listeria, etc.) |
| `MYCOTOXIN_OR_CHEMICAL_CONTAMINATION` | Mold-produced toxins or harmful chemical residues |
| `NUTRITIONAL_IMBALANCE_OR_TOXICITY` | Excess or deficiency of vitamins, minerals, or nutrients |
| `FOREIGN_MATERIAL_CONTAMINATION` | Physical contaminants (metal, plastic, bone fragments, etc.) |
| `LABELING_OR_UNDECLARED_INGREDIENT_ISSUE` | Missing allergen declarations or mislabeled ingredients |
| `QUALITY_OR_PROCESS_CONTROL_ISSUE` | Manufacturing defects not covered by other categories |

---

## Planned Data Sources

**Primary:**
- [FDA Animal & Veterinary Recalls / Withdrawals](https://www.fda.gov/animal-veterinary/safety-health/recalls-withdrawals)

**Fallback:**
- [openFDA Food Enforcement API](https://open.fda.gov/apis/food/enforcement/)

**Minimum target:** 200 labeled rows in the final training set.

---

## Embedding Model

[`sentence-transformers/all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
— frozen, no fine-tuning.

---

## Classifiers

- Dummy baseline (most-frequent / stratified)
- `OneVsRestClassifier(LogisticRegression)`
- `OneVsRestClassifier(LinearSVC)`
- `OneVsRestClassifier(RandomForestClassifier)`

---

## Evaluation Metrics

- Micro / Macro / Weighted F1
- Per-label Precision, Recall, F1
- Hamming Loss
- Subset Accuracy (exact match)

---

## Pipeline Overview

```
Phase 0  →  Repository initialization (this phase)
Phase 1  →  Data collection from FDA sources
Phase 2  →  Data inspection and filtering
Phase 3  →  Data cleaning and text construction
Phase 4  →  Rule-based label mapping + manual review
Phase 5  →  Dataset assembly and train/val/test split
Phase 6  →  Sentence embedding generation
Phase 7  →  Classifier training
Phase 8  →  Evaluation and error analysis
Phase 9  →  Hugging Face deployment (dataset, model, Space)
```

---

## Repository Structure

```
pet-food-recall-risk-classification/
├── README.md
├── requirements.txt
├── .gitignore
│
├── data/
│   ├── raw/            # Downloaded source files (gitignored)
│   ├── interim/        # Filtered / partially processed (gitignored)
│   ├── processed/      # Final cleaned dataset (gitignored)
│   └── embeddings/     # Precomputed numpy arrays (gitignored)
│
├── src/
│   ├── config.py           # Project constants
│   ├── collect_data.py     # Phase 1: download FDA recall data
│   ├── inspect_data.py     # Phase 2: basic stats and filtering review
│   ├── clean_data.py       # Phase 3: text cleaning and normalization
│   ├── label_mapping.py    # Phase 4: rule-based + manual label assignment
│   ├── build_dataset.py    # Phase 5: final CSV assembly + splits
│   ├── build_embeddings.py # Phase 6: generate sentence embeddings
│   ├── train_classifiers.py# Phase 7: train and save classifiers
│   ├── evaluate.py         # Phase 8: evaluation metrics
│   └── predict.py          # Inference on new text
│
├── models/
│   ├── classifiers/    # All trained classifier files (gitignored)
│   └── selected/       # Best selected model (gitignored)
│
├── results/            # Evaluation outputs, tables, plots
│
├── app/
│   ├── app.py          # Gradio demo (Hugging Face Space)
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
# Clone the repository
git clone https://github.com/<your-username>/pet-food-recall-risk-classification.git
cd pet-food-recall-risk-classification

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Workflow (phase by phase)

```bash
# Phase 1 — collect data
python src/collect_data.py --output data/raw/

# Phase 2 — inspect
python src/inspect_data.py --input data/raw/ --output data/interim/

# Phase 3 — clean
python src/clean_data.py --input data/interim/ --output data/interim/

# Phase 4 — label
python src/label_mapping.py --input data/interim/ --output data/interim/

# Phase 5 — build dataset
python src/build_dataset.py --input data/interim/ --output data/processed/

# Phase 6 — embeddings
python src/build_embeddings.py --input data/processed/ --output data/embeddings/

# Phase 7 — train
python src/train_classifiers.py --embeddings data/embeddings/ --output models/

# Phase 8 — evaluate
python src/evaluate.py --models models/ --embeddings data/embeddings/ --output results/

# Inference
python src/predict.py --brand "Brand X" --product "Dry dog food" --reason "Salmonella"
```

---

## Hugging Face Deployment

- **Dataset:** will be published to `hf.co/datasets/<username>/pet-food-recall-risk`
- **Model:** selected classifier + label binarizer saved and uploaded
- **Space:** Gradio app in `app/` deployed to `hf.co/spaces/<username>/pet-food-recall-risk-demo`

---

## Disclaimer

> This project is for **educational purposes only**. It does not provide veterinary advice,
> legal guidance, or product safety certification. Risk label predictions are generated by a
> machine learning model trained on historical recall text and may be incorrect or incomplete.
> Always consult official FDA recall notices and a qualified veterinarian for authoritative
> information about pet food safety.
