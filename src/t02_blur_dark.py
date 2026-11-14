from src.common.image_ops import (
    laplacian_variance,
    brightness_stats,
)

def extract_blur_dark_features(image):
    # Tính các chỉ số độ sáng
    stats = brightness_stats(image)

    # Trả về các đặc trưng của ảnh
    return {
        "blur": laplacian_variance(image),
        "frac_dark": stats["frac_dark"],
        "brightness": stats["mean"],
    }

def calculate_blur_score(
    blur_value,
    reference_blur_values,
):
    """
    Calculate a normalized blur suspicion score.

    Lower Laplacian variance means higher blur suspicion.

    Returns a score between 0 and 1.
    """
    import numpy as np

    reference = np.asarray(reference_blur_values, dtype=float)

    if reference.size == 0:
        raise ValueError("reference_blur_values cannot be empty")

    if not np.isfinite(reference).all():
        raise ValueError("reference_blur_values must be finite")

    if not np.isfinite(blur_value):
        raise ValueError("blur_value must be finite")

    # Percentile rank: proportion of reference values <= blur_value
    percentile = np.mean(reference <= blur_value)

    # Lower sharpness means higher blur suspicion
    return float(1.0 - percentile)


def get_blur_reference_values(
    dev_features,
    camera_id,
    light,
    min_group_size=10,
):
    """
    Select blur reference values using dev data only.

    Priority:
    1. Same camera_id and light, if enough samples.
    2. Same camera_id, if enough samples.
    3. All dev samples as fallback.
    """
    required_columns = {"camera_id", "light", "blur"}

    missing = required_columns - set(dev_features.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if min_group_size < 1:
        raise ValueError("min_group_size must be >= 1")

    exact_group = dev_features[
        (dev_features["camera_id"] == camera_id)
        & (dev_features["light"] == light)
    ]

    if len(exact_group) >= min_group_size:
        return exact_group["blur"].to_numpy(), "camera_light"

    camera_group = dev_features[
        dev_features["camera_id"] == camera_id
    ]

    if len(camera_group) >= min_group_size:
        return camera_group["blur"].to_numpy(), "camera"

    if len(dev_features) >= min_group_size:
        return dev_features["blur"].to_numpy(), "global_dev"

    raise ValueError("Not enough dev samples for blur reference")


if __name__ == "__main__":
    from pathlib import Path
    from src.common.image_ops import load_rgb

    root = Path("fixtures/t02_raw_qc")

    test_images = [
        "images/img_09_2.jpg",
        "images/img_18_3.jpg",
    ]

    for image_path in test_images:
        image = load_rgb(root / image_path)

        features = extract_blur_dark_features(image)

        print(f"\nImage: {image_path}")
        print(features)

def calculate_dark_score(frac_dark, brightness):
    """
    Calculate a darkness suspicion score between 0 and 1.

    A high dark-pixel fraction combined with low brightness
    indicates stronger darkness suspicion.

    This is a heuristic score, not a definitive defect label.
    """
    import numpy as np

    if not np.isfinite(frac_dark):
        raise ValueError("frac_dark must be finite")

    if not np.isfinite(brightness):
        raise ValueError("brightness must be finite")

    if not 0 <= frac_dark <= 1:
        raise ValueError("frac_dark must be between 0 and 1")

    if not 0 <= brightness <= 255:
        raise ValueError("brightness must be between 0 and 255")

    dark_fraction_score = frac_dark

    brightness_score = np.clip(
        (80.0 - brightness) / 65.0,
        0.0,
        1.0,
    )

    return float(
        dark_fraction_score * brightness_score
    )