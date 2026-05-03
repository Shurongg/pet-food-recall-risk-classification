# Pet Food Recall Risk Classifier — Hugging Face Space

This directory contains the Gradio demo app that will be deployed as a
[Hugging Face Space](https://huggingface.co/spaces).

## What this Space does

Accepts a pet food brand name, product description, and recall reason as input,
then predicts one or more risk labels from the taxonomy:

- `PATHOGEN_CONTAMINATION`
- `MYCOTOXIN_OR_CHEMICAL_CONTAMINATION`
- `NUTRITIONAL_IMBALANCE_OR_TOXICITY`
- `FOREIGN_MATERIAL_CONTAMINATION`
- `LABELING_OR_UNDECLARED_INGREDIENT_ISSUE`
- `QUALITY_OR_PROCESS_CONTROL_ISSUE`

## Status

**Not deployed yet.** The classifier model will be trained and uploaded in Phase 7–9
of the project pipeline.

## Deployment notes (Phase 9 TODO)

1. Train and evaluate classifiers (`src/train_classifiers.py`, `src/evaluate.py`)
2. Copy the selected model artifacts into this directory or load from the Hub
3. Update `app.py` to call the real `predict()` function
4. Push this directory to a new Hugging Face Space:
   ```bash
   huggingface-cli repo create pet-food-recall-risk-demo --type space --space_sdk gradio
   git subtree push --prefix app origin main
   ```

## Disclaimer

This tool is for educational purposes only and does not provide veterinary,
legal, or product safety certification advice.
