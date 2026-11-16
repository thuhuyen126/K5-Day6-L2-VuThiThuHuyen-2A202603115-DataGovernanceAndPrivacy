
from pathlib import Path

import pandas as pd

from src.common.image_ops import load_rgb
from src.t02_blur_dark import (
    extract_blur_dark_features,
    calculate_blur_score,
    calculate_dark_score,
    get_blur_reference_values,
)


def extract_dataset_features(
    images: pd.DataFrame,
    input_dir: Path,
) -> pd.DataFrame:
    """Extract Blur/Dark features for every image in the metadata."""

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
            f"Missing image metadata columns: {sorted(missing)}"
        )

    if images["image_id"].isna().any():
        raise ValueError("Missing image_id in metadata")

    if images["image_id"].duplicated().any():
        raise ValueError("Duplicate image_id in metadata")

    results = []

    for row in images.itertuples(index=False):
        image_path = input_dir / str(row.path)

        if not image_path.is_file():
            raise FileNotFoundError(image_path)

        image = load_rgb(image_path)
        features = extract_blur_dark_features(image)

        results.append({
            "image_id": row.image_id,
            "camera_id": row.camera_id,
            "light": row.light,
            "split": row.split,
            **features,
        })

    return pd.DataFrame(results)


def score_blur_dark(
    features: pd.DataFrame,
    dev_split: str = "dev",
    min_group_size: int = 10,
) -> pd.DataFrame:
    """Calculate Blur and Dark scores using DEV-only blur references."""

    required = {
        "image_id",
        "camera_id",
        "light",
        "split",
        "blur",
        "frac_dark",
        "brightness",
    }

    missing = required - set(features.columns)
    if missing:
        raise ValueError(
            f"Missing feature columns: {sorted(missing)}"
        )

    dev_features = features[
        features["split"] == dev_split
    ].copy()

    if dev_features.empty:
        raise ValueError(
            f"No reference images found for split={dev_split!r}"
        )

    results = []

    for row in features.itertuples(index=False):
        reference, reference_level = get_blur_reference_values(
            dev_features=dev_features,
            camera_id=row.camera_id,
            light=row.light,
            min_group_size=min_group_size,
        )

        blur_score = calculate_blur_score(
            blur_value=row.blur,
            reference_blur_values=reference,
        )

        dark_score = calculate_dark_score(
            frac_dark=row.frac_dark,
            brightness=row.brightness,
        )

        results.append({
            "image_id": row.image_id,
            "camera_id": row.camera_id,
            "light": row.light,
            "split": row.split,
            "blur": row.blur,
            "blur_score": blur_score,
            "blur_reference": reference_level,
            "frac_dark": row.frac_dark,
            "brightness": row.brightness,
            "dark_score": dark_score,
        })

    return pd.DataFrame(results)
