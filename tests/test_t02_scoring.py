
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.t02_scoring import (
    extract_dataset_features,
    score_blur_dark,
)


@pytest.fixture
def sample_images(tmp_path):
    """Create a small image dataset for isolated tests."""
    from PIL import Image

    image_dir = tmp_path / "images"
    image_dir.mkdir()

    rows = []

    # 12 DEV images ensure camera_light has enough reference samples.
    for i in range(12):
        image_id = f"dev_{i:02d}"
        filename = f"{image_id}.png"

        pixels = np.full(
            (180, 320, 3),
            100 + i,
            dtype=np.uint8,
        )

        Image.fromarray(pixels).save(image_dir / filename)

        rows.append({
            "image_id": image_id,
            "path": f"images/{filename}",
            "camera_id": "cam_A",
            "light": "day",
            "split": "dev",
        })

    # One EVAL image uses the DEV reference, not its own split.
    image_id = "eval_00"
    filename = f"{image_id}.png"

    pixels = np.full((180, 320, 3), 80, dtype=np.uint8)
    Image.fromarray(pixels).save(image_dir / filename)

    rows.append({
        "image_id": image_id,
        "path": f"images/{filename}",
        "camera_id": "cam_A",
        "light": "day",
        "split": "eval",
    })

    return pd.DataFrame(rows), tmp_path


def test_extract_dataset_features_returns_all_images(sample_images):
    images, input_dir = sample_images

    result = extract_dataset_features(images, input_dir)

    assert len(result) == len(images)
    assert result["image_id"].tolist() == images["image_id"].tolist()

    required_columns = {
        "image_id",
        "camera_id",
        "light",
        "split",
        "blur",
        "frac_dark",
        "brightness",
    }

    assert required_columns.issubset(result.columns)


def test_extract_dataset_features_rejects_missing_columns(sample_images):
    images, input_dir = sample_images
    images = images.drop(columns=["camera_id"])

    with pytest.raises(ValueError, match="Missing image metadata columns"):
        extract_dataset_features(images, input_dir)


def test_extract_dataset_features_rejects_duplicate_image_ids(sample_images):
    images, input_dir = sample_images
    images.loc[1, "image_id"] = images.loc[0, "image_id"]

    with pytest.raises(ValueError, match="Duplicate image_id"):
        extract_dataset_features(images, input_dir)


def test_extract_dataset_features_rejects_missing_image_id(sample_images):
    images, input_dir = sample_images
    images.loc[0, "image_id"] = None

    with pytest.raises(ValueError, match="Missing image_id"):
        extract_dataset_features(images, input_dir)


def test_extract_dataset_features_rejects_missing_file(sample_images):
    images, input_dir = sample_images
    images.loc[0, "path"] = "images/not_found.png"

    with pytest.raises(FileNotFoundError):
        extract_dataset_features(images, input_dir)


def test_score_blur_dark_returns_all_images(sample_images):
    images, input_dir = sample_images

    features = extract_dataset_features(images, input_dir)
    result = score_blur_dark(features)

    assert len(result) == len(images)
    assert set(result["image_id"]) == set(images["image_id"])

    required_columns = {
        "image_id",
        "blur_score",
        "blur_reference",
        "dark_score",
    }

    assert required_columns.issubset(result.columns)


def test_score_blur_dark_uses_dev_reference_for_eval(sample_images):
    images, input_dir = sample_images

    features = extract_dataset_features(images, input_dir)
    result = score_blur_dark(features)

    eval_result = result[result["split"] == "eval"]

    assert len(eval_result) == 1
    assert eval_result.iloc[0]["blur_reference"] == "camera_light"


def test_score_blur_dark_rejects_missing_dev_split(sample_images):
    images, input_dir = sample_images

    features = extract_dataset_features(images, input_dir)

    with pytest.raises(ValueError, match="No reference images"):
        score_blur_dark(features, dev_split="missing")


def test_score_blur_dark_produces_finite_scores(sample_images):
    images, input_dir = sample_images

    features = extract_dataset_features(images, input_dir)
    result = score_blur_dark(features)

    assert np.isfinite(result["blur_score"]).all()
    assert np.isfinite(result["dark_score"]).all()

    assert result["blur_score"].between(0, 1).all()
    assert result["dark_score"].between(0, 1).all()
