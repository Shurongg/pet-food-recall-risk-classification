# Pet Food Recall Risk Classification with Transformer Embeddings

*Assignment report — Information Retrieval*
*Author: TODO | Date: TODO | Word count: TODO / ~1000*

---

## Introduction

TODO: 2–3 sentences describing the problem, why it matters, and the approach.

- What is the task? (multi-label classification of FDA pet food recall text)
- Why is it relevant to Information Retrieval?
- Brief statement of the approach (frozen transformer embeddings + sklearn classifiers)

---

## Dataset Creation

TODO: Describe the dataset construction process concisely.

- Source(s) used and why
- Scope filtering decisions
- Number of records collected, filtered, and retained
- Label taxonomy and annotation strategy
- Final dataset size and label distribution
- Train / val / test split rationale

---

## Method

TODO: Describe the technical pipeline.

- Input text format
- Embedding model (sentence-transformers/all-MiniLM-L6-v2) and why it was chosen
- Classifiers evaluated (Dummy, LR, LinearSVC, RF — all OneVsRest)
- Per-label threshold tuning strategy
- No fine-tuning rationale

---

## Evaluation

TODO: Report results concisely.

- Evaluation metrics and why they were chosen for multi-label classification
- Results table (micro F1, macro F1, hamming loss, subset accuracy)
- Selected model and justification
- Per-label analysis of the selected model
- Key findings from error analysis

---

## Hugging Face Deployment

TODO: Describe the deployment artifacts.

- Dataset uploaded to Hugging Face Datasets
- Model artifacts uploaded
- Gradio Space demo description
- Link(s) to the published artifacts

---

## Reflection on AI Tool Use

TODO: Honest, critical reflection (required by the assignment).

- Which AI tools were used and for what?
- What was generated vs. written independently?
- What required correction or could not be delegated to AI?
- Effect on learning and understanding

---

## Limitations

TODO: Be honest about what the project does not do well.

- Dataset size and representativeness
- Label quality (rule-based annotation limitations)
- Model scope (only trained on FDA recalls; may not generalize)
- No fine-tuning of the embedding model
- Not a real safety tool — educational use only

---

## References

TODO: Add references in a consistent citation style.

- FDA Animal & Veterinary Recalls / Withdrawals
- openFDA Food Enforcement API documentation
- Reimers & Gurevych (2019) — Sentence-BERT
- scikit-learn documentation
- Any other papers or resources cited
