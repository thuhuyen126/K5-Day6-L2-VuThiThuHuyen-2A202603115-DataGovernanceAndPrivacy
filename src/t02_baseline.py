
"""T02 global Laplacian baseline.

Uses one global DEV-derived threshold across all cameras and lighting
conditions. Lower Laplacian variance means higher blur suspicion.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.image_ops import load_rgb, laplacian_variance


def run_global_laplacian_baseline(
    images: pd.DataFrame,
    input_dir: Path,
    dev_split: str = "dev",
    budget: int = 20,
) -> tuple[pd.DataFrame, float]:
    """Return DEV baseline predictions and one global Laplacian threshold."""

    required = {
        "image_id",
        "path",
        "camera_id",
        "light",
        "split",
    }
    missing = required - set(images.columns)

    if missing:
        raise ValueError(
            f"Missing metadata columns: {sorted(missing)}"
        )

    if budget < 1:
        raise ValueError("budget must be >= 1")

    dev = images[images["split"] == dev_split].copy()

    if dev.empty:
        raise ValueError(f"No images found for split={dev_split!r}")

    if dev["image_id"].duplicated().any():
        raise ValueError("Duplicate image_id in DEV metadata")

    if budget > len(dev):
        raise ValueError(
            f"budget={budget} exceeds DEV sample count={len(dev)}"
        )

    rows = []

    for row in dev.itertuples(index=False):
        image_path = input_dir / str(row.path)

        if not image_path.is_file():
            raise FileNotFoundError(image_path)

        image = load_rgb(image_path)
        blur = laplacian_variance(image)

        rows.append({
            "image_id": row.image_id,
            "camera_id": row.camera_id,
            "light": row.light,
            "blur": blur,
        })

    features = pd.DataFrame(rows)

    # One global threshold: the B-th lowest Laplacian value.
    threshold = float(
        features["blur"].nsmallest(budget).max()
    )

    # Higher score = more suspicious.
    # Use continuous inverse Laplacian ranking to preserve ordering.
    features["score"] = -features["blur"]

    predictions = features[
        ["image_id", "score"]
    ].copy()

    return predictions, threshold
