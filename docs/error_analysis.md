# Error Analysis

Final held-out test evaluation for the selected validation-based model.

---

## Evaluation Setup

- **Phase:** Phase 8 — Final Test Evaluation
- **Selected model:** `logistic_regression`
- **Model file:** `models/classifiers/logistic_regression.joblib`
- **Thresholds:** validation-selected thresholds from `models/selected/thresholds.json`
- **Test rows:** 15
- **Final labels:** `PATHOGEN_CONTAMINATION`, `CHEMICAL_OR_NUTRITIONAL_RISK`,
  `PHYSICAL_OR_QUALITY_ISSUE`
- **Important constraint:** the test set was evaluated once. No training,
  threshold tuning, model selection, embedding regeneration, label changes, or
  synthetic data were performed during Phase 8.

---

## Overall Test Performance

| Model | Micro F1 | Macro F1 | Weighted F1 | Hamming Loss | Subset Accuracy |
|---|---:|---:|---:|---:|---:|
| logistic_regression | 0.875 | 0.841 | 0.881 | 0.089 | 0.800 |

---

## Per-Label Performance

| Label | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| PATHOGEN_CONTAMINATION | 1.000 | 1.000 | 1.000 | 8 |
| CHEMICAL_OR_NUTRITIONAL_RISK | 1.000 | 0.750 | 0.857 | 4 |
| PHYSICAL_OR_QUALITY_ISSUE | 0.600 | 0.750 | 0.667 | 4 |

---

## Confusion Matrix Summary

| Label | TP | FP | FN | TN |
|---|---:|---:|---:|---:|
| PATHOGEN_CONTAMINATION | 8 | 0 | 0 | 7 |
| CHEMICAL_OR_NUTRITIONAL_RISK | 3 | 0 | 1 | 11 |
| PHYSICAL_OR_QUALITY_ISSUE | 3 | 2 | 1 | 9 |

---

## Per-Label Observations

- `PATHOGEN_CONTAMINATION` was strongest on the held-out split, with no false
  positives or false negatives. Pathogen terms such as Salmonella, bacteria, and
  microbial wording are distinctive in this dataset.
- `CHEMICAL_OR_NUTRITIONAL_RISK` had one false negative. The missed example was
  a heavy-metal recall: `Pet Food Deer chew sticks - Lead contamination`.
- `PHYSICAL_OR_QUALITY_ISSUE` was the weakest final label. It produced two false
  positives and one false negative, mostly around short RASFF regulatory/hazard
  phrasing where process-control, labeling, and physical-quality signals overlap.

---

## Misclassified Records

| Source ID | True labels | Predicted labels | Observation |
|---|---|---|---|
| `2022.7669` | CHEMICAL_OR_NUTRITIONAL_RISK | CHEMICAL_OR_NUTRITIONAL_RISK; PHYSICAL_OR_QUALITY_ISSUE | Non-approved cannabidiol feed additive was correctly identified as chemical/nutritional but also over-predicted as physical/quality. |
| `2021.0486` | CHEMICAL_OR_NUTRITIONAL_RISK | PHYSICAL_OR_QUALITY_ISSUE | Lead/heavy-metal contamination was missed as chemical/nutritional and confused with physical/quality. |
| `2021.3773` | PATHOGEN_CONTAMINATION; PHYSICAL_OR_QUALITY_ISSUE | PATHOGEN_CONTAMINATION | Multi-label row with bacteria, no labeling, and defective closure kept the pathogen label but missed physical/quality. |

---

## Small-Data Limitation

The test set has only 15 rows and 16 positive label assignments. Per-label
metrics are therefore highly sensitive to one or two examples. The final
three-label taxonomy improved viability compared with the original sparse
six-label taxonomy, but results should still be interpreted as assignment-scale
evidence rather than robust production performance.

---

## Takeaways

- The selected model separates pathogen recalls well in this small held-out set.
- Chemical/nutritional and physical/quality boundaries remain the most fragile,
  especially for RASFF records with terse regulatory language.
- Later improvements should focus on more labeled examples for chemical,
  additive, heavy-metal, labeling, and process-control cases before increasing
  model complexity.
