
from pathlib import Path

import pandas as pd

from src.t02_baseline import run_global_laplacian_baseline
from src.t02_scoring import (
    extract_dataset_features,
    score_blur_dark,
)


root = Path("fixtures/t02_raw_qc")
budget = 20

images = pd.read_csv(root / "images.csv")
dev_images = images[images["split"] == "dev"].copy()

print("===== DATASET =====")
print("DEV images:", len(dev_images))
print("Review budget:", budget)

# 1. Global Laplacian baseline.
baseline, threshold = run_global_laplacian_baseline(
    images=images,
    input_dir=root,
    dev_split="dev",
    budget=budget,
)

# 2. Blur/Dark PoC V1.
features = extract_dataset_features(images, root)
scored = score_blur_dark(features, dev_split="dev")

poc = scored[scored["split"] == "dev"].copy()
poc["score"] = poc[
    ["blur_score", "dark_score"]
].max(axis=1)

# 3. Save predictions.
output_dir = Path("out/dev")
output_dir.mkdir(parents=True, exist_ok=True)

baseline.to_csv(
    output_dir / "baseline_laplacian_v1.csv",
    index=False,
)

poc[["image_id", "score"]].to_csv(
    output_dir / "poc_blur_dark_v1.csv",
    index=False,
)

# 4. Select top-B with stable ordering.
baseline_top = (
    baseline.sort_values(
        "score", ascending=False, kind="mergesort"
    )
    .head(budget)
)

poc_top = (
    poc.sort_values(
        "score", ascending=False, kind="mergesort"
    )
    .head(budget)
)

baseline_ids = set(baseline_top["image_id"])
poc_ids = set(poc_top["image_id"])

intersection = baseline_ids & poc_ids
union = baseline_ids | poc_ids

overlap = len(intersection)
jaccard = overlap / len(union) if union else 0.0

# 5. Attach metadata for slice analysis.
baseline_detail = baseline_top.merge(
    dev_images[["image_id", "camera_id", "light"]],
    on="image_id",
    validate="one_to_one",
)

# PoC already contains camera_id and light from score_blur_dark().
poc_detail = poc_top.copy()

# 6. Build report without optional tabulate dependency.
def as_text_table(dataframe):
    return (
        "```text\n"
        + dataframe.to_string(index=False)
        + "\n```"
    )


baseline_slices = (
    baseline_detail.groupby(["camera_id", "light"])
    .size()
    .rename("count")
    .reset_index()
)

poc_slices = (
    poc_detail.groupby(["camera_id", "light"])
    .size()
    .rename("count")
    .reset_index()
)

report = [
    "# T02 DEV: Global Laplacian Baseline vs Blur/Dark PoC V1",
    "",
    "## Protocol",
    "",
    f"- Split: DEV only ({len(dev_images)} images)",
    f"- Review budget: B={budget}",
    "- Baseline: one global Laplacian threshold across all cameras/lights",
    "- PoC: max(blur_score, dark_score), with DEV-only Blur references",
    "- No ground-truth labels used",
    "",
    "## Global Laplacian baseline",
    "",
    f"- Global threshold (20th lowest Laplacian value): {threshold:.6f}",
    f"- Top-{budget} candidates: {len(baseline_top)}",
    "",
    "## Ranking overlap",
    "",
    f"- Shared images: {overlap}/{budget}",
    f"- Jaccard similarity: {jaccard:.4f}",
    "",
    "## Baseline top-20",
    "",
    as_text_table(baseline_detail),
    "",
    "## PoC top-20",
    "",
    as_text_table(poc_detail),
    "",
    "## Camera/light composition",
    "",
    "### Baseline",
    "",
    as_text_table(baseline_slices),
    "",
    "### PoC",
    "",
    as_text_table(poc_slices),
    "",
    "## Interpretation limitation",
    "",
    "This is an unlabeled DEV ranking comparison, not a defect-recall "
    "or precision evaluation. Ground-truth labels are required for "
    "Defect Recall@20 and Precision@20.",
]

report_path = Path("reports/table_dev_baseline_vs_poc.md")
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text("\n".join(report), encoding="utf-8")

print("\n===== BASELINE =====")
print("Global threshold:", threshold)
print("Top-20 rows:", len(baseline_top))

print("\n===== POC =====")
print("Top-20 rows:", len(poc_top))

print("\n===== OVERLAP =====")
print("Shared images:", overlap, "/", budget)
print("Jaccard:", round(jaccard, 4))

print("\n===== BASELINE CAMERA/LIGHT =====")
print(
    baseline_detail.groupby(
        ["camera_id", "light"]
    ).size()
)

print("\n===== POC CAMERA/LIGHT =====")
print(
    poc_detail.groupby(
        ["camera_id", "light"]
    ).size()
)

print("\nSaved:")
print(output_dir / "baseline_laplacian_v1.csv")
print(output_dir / "poc_blur_dark_v1.csv")
print(report_path)
