"""
Inference — Predict Risk Labels for New Text

Loads the selected trained classifier and generates multi-label
risk predictions for a single recall description provided via CLI arguments.

Used by the Gradio app (app/app.py) as the backend prediction function.

TODO (Phase 9 / deployment):
  - Load the selected classifier from models/selected/
  - Load the label binarizer from models/classifiers/label_binarizer.pkl
  - Load per-label thresholds from models/selected/
  - Encode the input text using EMBEDDING_MODEL_NAME (sentence-transformers)
  - Apply the classifier and thresholds to get binary label predictions
  - Return predicted label names and (if available) confidence scores
"""

import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="Predict risk labels for a new pet food recall description."
    )
    parser.add_argument("--brand", required=True, help="Brand name(s)")
    parser.add_argument("--product", required=True, help="Product description")
    parser.add_argument("--reason", required=True, help="Recall reason description")
    parser.add_argument(
        "--model-dir",
        default="models/selected/",
        help="Directory containing the selected trained model (default: models/selected/)",
    )
    return parser.parse_args()


def predict(brand: str, product: str, reason: str, model_dir: str = "models/selected/"):
    """Return predicted risk labels for the given recall description fields.

    TODO: implement full inference pipeline.
    """
    # TODO: implement inference logic
    return []


def main():
    args = parse_args()
    # TODO: call predict() and print results
    print("[predict] Inference not implemented yet.")
    print(f"  Brand:   {args.brand}")
    print(f"  Product: {args.product}")
    print(f"  Reason:  {args.reason}")


if __name__ == "__main__":
    main()
