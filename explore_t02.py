
import pandas as pd
from pathlib import Path

from src.common.image_ops import (
    load_rgb,
    laplacian_variance,
    brightness_stats,
)

# Load metadata
root = Path("fixtures/t02_raw_qc")
images = pd.read_csv(root / "images.csv")

# Only inspect dev split
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
    })

features = pd.DataFrame(rows)

print("=== 10 LOWEST BLUR ===")
print(
    features.nsmallest(10, "blur")
    .round(3)
    .to_string(index=False)
)

print("\n=== 10 HIGHEST DARK FRACTION ===")
print(
    features.nlargest(10, "frac_dark")
    .round(3)
    .to_string(index=False)
)
