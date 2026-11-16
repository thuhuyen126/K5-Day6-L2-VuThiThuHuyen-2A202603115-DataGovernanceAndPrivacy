
from pathlib import Path
import pandas as pd

from src.t02_scoring import (
    extract_dataset_features,
    score_blur_dark,
)

root = Path("fixtures/t02_raw_qc")
images = pd.read_csv(root / "images.csv")

print("===== EXTRACT FEATURES =====")
features = extract_dataset_features(images, root)
print("Feature rows:", len(features))
print(features.head().to_string(index=False))

print("\n===== SCORE BLUR/DARK =====")
scored = score_blur_dark(features, dev_split="dev")
print("Scored rows:", len(scored))

print("\n===== BLUR REFERENCE LEVELS =====")
print(scored["blur_reference"].value_counts(dropna=False))

print("\n===== DARK V1 CONSISTENCY =====")
old = pd.read_csv("out/dev/dark_v1.csv")
dev = scored[scored["split"] == "dev"]

comparison = dev.merge(
    old,
    on="image_id",
    suffixes=("_new", "_old"),
    validate="one_to_one",
)

comparison["abs_diff"] = (
    comparison["dark_score"] - comparison["score"]
).abs()

print("Compared DEV rows:", len(comparison))
print("Maximum absolute difference:", comparison["abs_diff"].max())
print(
    "Dark scores identical:",
    comparison["abs_diff"].max() < 1e-12,
)

print("\n===== SCORE VALIDATION =====")
print("Blur score finite:", scored["blur_score"].map(pd.notna).all())
print("Dark score finite:", scored["dark_score"].map(pd.notna).all())
print(
    "Dark score range:",
    scored["dark_score"].min(),
    "to",
    scored["dark_score"].max(),
)
