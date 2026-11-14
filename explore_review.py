
import pandas as pd
from pathlib import Path

from src.common.image_ops import (
    load_rgb,
    laplacian_variance,
    brightness_stats,
)
from src.common.review import make_review_queue
from src.common.contact_sheet import render_contact_sheet

root = Path("fixtures/t02_raw_qc")
images = pd.read_csv(root / "images.csv")
dev = images[images["split"] == "dev"]

rows = []

for row in dev.itertuples():
    image = load_rgb(root / row.path)
    stats = brightness_stats(image)

    rows.append({
        "image_id": row.image_id,
        "camera_id": row.camera_id,
        "light": row.light,
        "blur": laplacian_variance(image),
        "frac_dark": stats["frac_dark"],
        "brightness": stats["mean"],
        "path": row.path,
    })

features = pd.DataFrame(rows)

# Select suspicious candidates from both feature groups
blur_candidates = features.nsmallest(10, "blur")
dark_candidates = features.nlargest(10, "frac_dark")

candidates = (
    pd.concat([blur_candidates, dark_candidates])
    .drop_duplicates("image_id")
    .copy()
)

candidates["score"] = (
    candidates["frac_dark"]
    + 1 / (1 + candidates["blur"])
)

candidates["reason"] = "blur_or_dark_candidate"
candidates["suggested_action"] = "review"

queue = make_review_queue(
    candidates,
    id_col="image_id",
    score_col="score",
    budget=len(candidates),
    reason_col="reason",
    evidence_col="path",
)

output = Path("out/exploration")
output.mkdir(parents=True, exist_ok=True)

render_contact_sheet(
    queue,
    output / "blur_dark_review.html",
    image_root=root,
    title="T02 - Blur and Dark Exploration",
    fields=("rank", "item_id", "score", "reason", "evidence_path"),
)

print("Candidates:", len(candidates))
print("Contact sheet:", output / "blur_dark_review.html")
print(candidates[
    ["image_id", "camera_id", "light", "blur", "frac_dark"]
].round(3).to_string(index=False))
