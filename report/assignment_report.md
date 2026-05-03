# Pet Food Recall Risk Classification with Transformer Embeddings

*Assignment report — Information Retrieval*
*Date: 2026-05-03*

---

## Introduction

This project frames pet food recall triage as supervised multi-label text classification: given a recall record's brand, product, and reason text, predict one or more risk categories. The pipeline uses frozen sentence-transformer embeddings fed into scikit-learn classifiers, keeping the approach lightweight and reproducible while meeting the assignment requirements for a custom dataset, embeddings, multiple trained classifiers, and a working demo.

---

## Dataset Creation

Records were collected from five official public sources: FDA Animal & Veterinary Recalls (49 rows), EU RASFF manual export (60 rows), UK FSA Food Alerts (1,314 rows), openFDA Food Enforcement API (107 rows), and Canada CFIA/Consumer Product Safety (10,315 rows). Strict pet-food scope filtering — requiring explicit phrases such as "dog food", "cat food", or "pet treat" — reduced 11,845 raw rows to 117 candidates. Rule-based keyword patterns over the recall reason and hazard fields assigned six detailed labels, which were then consolidated into three due to class sparsity. Fourteen records with ambiguous reasons were excluded as uncertain, leaving **103 labeled rows**.

| Label | Positive count |
|---|---:|
| `PATHOGEN_CONTAMINATION` | 60 |
| `CHEMICAL_OR_NUTRITIONAL_RISK` | 20 |
| `PHYSICAL_OR_QUALITY_ISSUE` | 26 |

A seed search produced a 70/15/15 train/validation/test split (73/15/15 rows) ensuring all three labels appear in every split. The small final size reflects the genuine scarcity of official pet-food-specific recall records.

---

## Method

Each record is encoded as:

```
Brand: {brand_names}. Product: {product_description}. Recall reason: {recall_reason_description}.
```

The text is embedded with the frozen pre-trained model `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions). The encoder is not fine-tuned; frozen embeddings reduce overfitting risk on the small dataset. Four `OneVsRestClassifier` models were trained and compared on the validation split: Dummy baseline (most-frequent), Logistic Regression, Linear SVC, and Random Forest. Per-label prediction thresholds were tuned over 0.20–0.80 on the validation set for models with probability output.

---

## Evaluation

**Validation results:**

| Model | Micro F1 | Macro F1 | Hamming Loss | Subset Acc. |
|---|---:|---:|---:|---:|
| Dummy baseline | 0.516 | 0.232 | 0.333 | 0.467 |
| Logistic Regression | 0.941 | 0.933 | 0.044 | 0.867 |
| Linear SVC | 0.903 | 0.857 | 0.067 | 0.800 |
| Random Forest | 0.941 | 0.933 | 0.044 | 0.867 |

Logistic Regression and Random Forest tied on validation macro F1. Logistic Regression was selected as the final model because it supports probability scores, enabling per-label threshold tuning.

**Test results (held-out, evaluated once):**

| Metric | Value |
|---|---:|
| Micro F1 | 0.875 |
| Macro F1 | 0.841 |
| Weighted F1 | 0.881 |
| Hamming Loss | 0.089 |
| Subset Accuracy | 0.800 |

**Per-label F1 on test set:**

| Label | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| `PATHOGEN_CONTAMINATION` | 1.000 | 1.000 | 1.000 | 8 |
| `CHEMICAL_OR_NUTRITIONAL_RISK` | 1.000 | 0.750 | 0.857 | 4 |
| `PHYSICAL_OR_QUALITY_ISSUE` | 0.600 | 0.750 | 0.667 | 4 |

Pathogen recalls were distinguished with perfect precision and recall; their keyword signals (Salmonella, Listeria) are distinctive. The weakest label, `PHYSICAL_OR_QUALITY_ISSUE`, consolidates heterogeneous subtypes whose recall language overlaps. With only 15 test rows, all metrics should be interpreted as assignment-scale evidence, not robust production estimates.

---

## Hugging Face Deployment

- **Dataset:** https://huggingface.co/datasets/ShurongSR/pet-food-recall-risk
- **Model:** https://huggingface.co/ShurongSR/pet-food-recall-risk-classifier
- **Demo Space:** https://huggingface.co/spaces/ShurongSR/pet-food-recall-risk-demo
- **GitHub:** https://github.com/Shurongg/pet-food-recall-risk-classification

The model repository contains the trained `OneVsRestClassifier(LogisticRegression)` in joblib format, per-label thresholds, and evaluation metrics. The Gradio demo accepts brand, product, and reason text and returns predicted risk labels. This system is for educational purposes only and does not constitute veterinary, legal, or product safety advice.

---

## Reflection on AI Tool Use

Claude (Anthropic) was used to scaffold pipeline scripts, debug deployment, and draft documentation throughout all phases. AI assistance accelerated boilerplate tasks — data-collection scripts, scikit-learn pipelines, dataset cards, and this report.

Decisions that required human judgement:
- **Task design** — choosing multi-label framing and defining semantically coherent label boundaries.
- **Label consolidation** — recognising that six detailed labels were too sparse for 103 records and deciding which to merge.
- **Data-source selection and small-data acceptance** — evaluating sources for scope and licensing, and deciding not to add synthetic data to inflate size.
- **Output verification** — all AI-generated code was run and results checked against expected counts and metrics before each phase was accepted.

AI tools reduce friction on implementation but do not substitute for task-design, data-quality, and interpretive judgements.

---

## Limitations

1. **Small dataset and test set.** At 103 rows with a 15-row test set, metrics are sensitive to individual examples.
2. **Rule-based labeling.** Labels were assigned by keyword patterns without expert validation; borderline cases were excluded rather than annotated, introducing potential selection bias.
3. **Consolidated labels.** The three-label taxonomy improves trainability but loses granularity across subtypes such as heavy-metal contamination and labeling errors.
4. **No embedding fine-tuning.** The frozen encoder may not capture atypical recall phrasings; fine-tuning on in-domain text could improve minority-label recall.
5. **Not a safety tool.** The model predicts risk categories from text and may be incorrect or incomplete.

---

## References

- U.S. Food and Drug Administration. *Animal & Veterinary Recalls / Withdrawals*. https://www.fda.gov/animal-veterinary/safety-health/recalls-withdrawals
- European Commission. *RASFF — Food and Feed Safety Alerts*. https://webgate.ec.europa.eu/rasff-window
- UK Food Standards Agency. *Food Alerts API*. https://data.food.gov.uk/food-alerts
- Government of Canada. *Health and Consumer Product Recalls and Safety Alerts*. https://recalls-rappels.canada.ca
- Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. *EMNLP 2019*. https://arxiv.org/abs/1908.10084
- Pedregosa, F., et al. (2011). Scikit-learn: Machine Learning in Python. *JMLR*, 12, 2825–2830.
- `sentence-transformers/all-MiniLM-L6-v2`. Hugging Face Hub. https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
