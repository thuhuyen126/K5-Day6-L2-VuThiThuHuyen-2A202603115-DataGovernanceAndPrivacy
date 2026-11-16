
from pathlib import Path

import pandas as pd

from src.common.contact_sheet import render_contact_sheet
from src.common.image_ops import load_rgb
from src.t02_blur_dark import (
    extract_blur_dark_features,
    calculate_dark_score,
)


ROOT = Path("fixtures/t02_raw_qc")

# Read image metadata
images = pd.read_csv(ROOT / "images.csv")

# Use dev split only
dev_images = images[images["split"] == "dev"].copy()

results = []

for row in dev_images.itertuples(index=False):
    image = load_rgb(ROOT / row.path)

    features = extract_blur_dark_features(image)

    dark_score = calculate_dark_score(
        frac_dark=features["frac_dark"],
        brightness=features["brightness"],
    )

    results.append({
        "image_id": row.image_id,
        "camera_id": row.camera_id,
        "light": row.light,
        **features,
        "dark_score": dark_score,
    })

df = pd.DataFrame(results)

# Export Dark V1 scores for development and pipeline integration
dark_v1 = df[["image_id", "dark_score"]].rename(
    columns={"dark_score": "score"}
)

output_dir = Path("out/dev")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "dark_v1.csv"
dark_v1.to_csv(output_file, index=False)

print(f"\nDark V1 predictions saved: {output_file}")
print(f"Number of predictions: {len(dark_v1)}")
print(dark_v1.head().to_string(index=False))

print("\n===== DEV DARK SCORE DISTRIBUTION =====")
print(
    df["dark_score"]
    .describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9])
    .round(3)
)

print("\n===== DARK SCORE BY CAMERA =====")
print(
    df.groupby("camera_id")["dark_score"]
    .agg(["count", "mean", "median", "max"])
    .round(3)
)

print("\n===== DARK SCORE BY LIGHT =====")
print(
    df.groupby("light")["dark_score"]
    .agg(["count", "mean", "median", "max"])
    .round(3)
)

print("\n===== DARK SCORE BY CAMERA AND LIGHT =====")
print(
    df.groupby(["camera_id", "light"])["dark_score"]
    .agg(["count", "mean", "median", "max"])
    .round(3)
)

print("\n===== TOP 10 HIGHEST DARK SCORES =====")
print(
    df.sort_values("dark_score", ascending=False)[
        ["image_id", "camera_id", "light", "frac_dark",
         "brightness", "dark_score"]
    ]
    .head(10)
    .round(3)
)

# Select top 6 highest dark scores
top_dark = df.nlargest(6, "dark_score")

# Include all night images
night_images = df[df["light"] == "night"]

# Combine and remove duplicates
review_df = (
    pd.concat([top_dark, night_images])
    .drop_duplicates(subset="image_id")
    .copy()
)

# Prepare contact sheet columns
review_df["rank"] = range(1, len(review_df) + 1)
review_df["item_id"] = review_df["image_id"]
review_df["score"] = review_df["dark_score"]
review_df["reason"] = "High darkness suspicion"
review_df["suggested_action"] = "human_review"
review_df["slice"] = (
    review_df["camera_id"] + "/" + review_df["light"]
)

# Map image IDs to their original image paths
path_map = images.set_index("image_id")["path"]
review_df["evidence_path"] = review_df["image_id"].map(path_map)

# Generate offline HTML contact sheet
output_path = render_contact_sheet(
    queue=review_df,
    out_html="reports/dark_review_candidates.html",
    image_col="evidence_path",
    fields=[
        "rank",
        "item_id",
        "score",
        "camera_id",
        "light",
        "frac_dark",
        "brightness",
        "reason",
        "suggested_action",
        "slice",
    ],
    title="T02 - Dark Feature Human Review",
    image_root=ROOT,
)

print(f"\nContact sheet created: {output_path}")
print(f"Number of images for review: {len(review_df)}")

# Compare dark scores with human review decisions
reviewed = pd.read_csv(
    Path("reports/review_queue_reviewed.csv")
)

review_comparison = df.merge(
    reviewed[
        ["item_id", "reviewer_decision", "review_note"]
    ],
    left_on="image_id",
    right_on="item_id",
    how="inner",
)

print("\n===== DARK SCORE VS HUMAN REVIEW =====")
print(
    review_comparison[
        [
            "image_id",
            "camera_id",
            "light",
            "frac_dark",
            "brightness",
            "dark_score",
            "reviewer_decision",
        ]
    ]
    .sort_values("dark_score", ascending=False)
    .round(3)
    .to_string(index=False)
)

print("\n===== MEAN DARK SCORE BY REVIEW DECISION =====")
print(
    review_comparison.groupby("reviewer_decision")[
        "dark_score"
    ]
    .agg(["count", "mean", "median", "max"])
    .round(3)
)