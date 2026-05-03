"""
Project-wide constants for the pet food recall risk classification pipeline.
Import this module from any other src/ script instead of hard-coding values.
"""

# ---------------------------------------------------------------------------
# Label taxonomy
# ---------------------------------------------------------------------------
LABEL_COLUMNS = [
    "PATHOGEN_CONTAMINATION",
    "MYCOTOXIN_OR_CHEMICAL_CONTAMINATION",
    "NUTRITIONAL_IMBALANCE_OR_TOXICITY",
    "FOREIGN_MATERIAL_CONTAMINATION",
    "LABELING_OR_UNDECLARED_INGREDIENT_ISSUE",
    "QUALITY_OR_PROCESS_CONTROL_ISSUE",
]

# Consolidated modeling taxonomy for the small-data setting.
FINAL_LABEL_COLUMNS = [
    "PATHOGEN_CONTAMINATION",
    "CHEMICAL_OR_NUTRITIONAL_RISK",
    "PHYSICAL_OR_QUALITY_ISSUE",
]

# ---------------------------------------------------------------------------
# Embedding model
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Input text template
# ---------------------------------------------------------------------------
INPUT_TEXT_TEMPLATE = (
    "Brand: {brand_names}. "
    "Product: {product_description}. "
    "Recall reason: {recall_reason_description}."
)

# ---------------------------------------------------------------------------
# Dataset size constraints
# ---------------------------------------------------------------------------
# Original assignment target. Kept to document the small-data limitation.
MIN_FINAL_ROWS = 200

# Realistic minimum for the closed-source, strictly filtered candidate pool.
MIN_FINAL_ROWS_SMALL_DATA = 80

MIN_POSITIVE_EXAMPLES_PER_LABEL = 20
