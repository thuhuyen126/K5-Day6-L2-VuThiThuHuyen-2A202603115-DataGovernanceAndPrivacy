
import numpy as np

from src.t02_blur_dark import get_blur_reference_values
from src.t02_blur_dark import extract_blur_dark_features


def test_feature_extraction_returns_required_keys():
    image = np.zeros((180, 320, 3), dtype=np.uint8)

    result = extract_blur_dark_features(image)

    assert set(result.keys()) == {
        "blur",
        "frac_dark",
        "brightness",
    }


def test_dark_image_has_high_dark_fraction():
    image = np.zeros((180, 320, 3), dtype=np.uint8)

    result = extract_blur_dark_features(image)

    assert result["frac_dark"] == 1.0
    assert result["brightness"] == 0.0


def test_feature_values_are_valid():
    image = np.full((180, 320, 3), 128, dtype=np.uint8)

    result = extract_blur_dark_features(image)

    assert result["blur"] >= 0
    assert 0 <= result["frac_dark"] <= 1
    assert 0 <= result["brightness"] <= 255


import pytest

from src.t02_blur_dark import calculate_blur_score


def test_blur_score_is_high_for_low_sharpness():
    score = calculate_blur_score(
        100,
        [100, 200, 300, 400, 500],
    )

    assert score == pytest.approx(0.8)


def test_blur_score_is_zero_for_highest_reference_value():
    score = calculate_blur_score(
        500,
        [100, 200, 300, 400, 500],
    )

    assert score == pytest.approx(0.0)


def test_blur_score_is_between_zero_and_one():
    score = calculate_blur_score(
        250,
        [100, 200, 300, 400, 500],
    )

    assert 0.0 <= score <= 1.0


def test_blur_score_rejects_empty_reference():
    with pytest.raises(ValueError):
        calculate_blur_score(100, [])


def test_blur_score_rejects_non_finite_reference():
    with pytest.raises(ValueError):
        calculate_blur_score(100, [100, float("nan")])


def test_blur_score_rejects_non_finite_input():
    with pytest.raises(ValueError):
        calculate_blur_score(float("nan"), [100, 200, 300])


import pandas as pd


def test_blur_reference_uses_camera_and_light():
    data = pd.DataFrame({
        "camera_id": ["cam_A"] * 12 + ["cam_B"] * 12,
        "light": ["day"] * 12 + ["day"] * 12,
        "blur": list(range(12)) + list(range(100, 112)),
    })

    values, source = get_blur_reference_values(
        data, "cam_A", "day"
    )

    assert source == "camera_light"
    assert len(values) == 12
    assert values[0] == 0


def test_blur_reference_falls_back_to_camera():
    data = pd.DataFrame({
        "camera_id": ["cam_B"] * 20,
        "light": ["day"] * 12 + ["night"] * 8,
        "blur": list(range(20)),
    })

    values, source = get_blur_reference_values(
        data, "cam_B", "night"
    )

    assert source == "camera"
    assert len(values) == 20



def test_blur_reference_falls_back_to_global_dev():
    data = pd.DataFrame({
        "camera_id": ["cam_A"] * 4 + ["cam_B"] * 8,
        "light": ["day"] * 4 + ["night"] * 8,
        "blur": list(range(12)),
    })

    values, source = get_blur_reference_values(
        data, "cam_A", "night"
    )

    assert source == "global_dev"
    assert len(values) == 12



def test_blur_reference_rejects_missing_columns():
    data = pd.DataFrame({
        "camera_id": ["cam_A"],
        "light": ["day"],
    })

    with pytest.raises(ValueError):
        get_blur_reference_values(data, "cam_A", "day")

from src.t02_blur_dark import calculate_dark_score


def test_dark_score_is_zero_for_bright_image():
    score = calculate_dark_score(
        frac_dark=0.0,
        brightness=120.0,
    )

    assert score == pytest.approx(0.0)


def test_dark_score_is_high_for_very_dark_image():
    score = calculate_dark_score(
        frac_dark=0.9,
        brightness=15.0,
    )

    assert score > 0.8


def test_dark_score_is_between_zero_and_one():
    score = calculate_dark_score(
        frac_dark=0.5,
        brightness=60.0,
    )

    assert 0.0 <= score <= 1.0


def test_dark_score_rejects_invalid_fraction():
    with pytest.raises(ValueError):
        calculate_dark_score(
            frac_dark=1.5,
            brightness=60.0,
        )


def test_dark_score_rejects_invalid_brightness():
    with pytest.raises(ValueError):
        calculate_dark_score(
            frac_dark=0.5,
            brightness=300.0,
        )