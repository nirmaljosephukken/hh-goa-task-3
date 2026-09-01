from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class ImageMatch:
    matches: bool
    hash_distance: int
    aspect_ratio_delta: float
    crop_similarity: float


def _difference_hash(path: str | Path) -> tuple[int, float]:
    """Create a compact perceptual hash for comparing near-duplicate images."""
    with Image.open(path) as image:
        width, height = image.size
        aspect_ratio = width / height
        grayscale = image.convert("L").resize((17, 16), Image.Resampling.LANCZOS)

    pixels = list(grayscale.get_flattened_data())
    bits = 0
    for row in range(16):
        offset = row * 17
        for column in range(16):
            bits = (bits << 1) | int(pixels[offset + column] > pixels[offset + column + 1])

    return bits, aspect_ratio


def _grayscale_array(path: str | Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("L"), dtype=np.uint8)


def _crop_to_aspect_ratio(
    image: np.ndarray, target_ratio: float, position: float
) -> np.ndarray:
    height, width = image.shape
    current_ratio = width / height

    if current_ratio > target_ratio:
        crop_width = round(height * target_ratio)
        start = round((width - crop_width) * position)
        return image[:, start : start + crop_width]

    crop_height = round(width / target_ratio)
    start = round((height - crop_height) * position)
    return image[start : start + crop_height, :]


def _resize_for_comparison(image: np.ndarray) -> np.ndarray:
    return np.asarray(
        Image.fromarray(image).resize((64, 64), Image.Resampling.LANCZOS),
        dtype=np.float32,
    )


def _visual_similarity(first: np.ndarray, second: np.ndarray) -> float:
    difference = np.mean(
        np.abs(_resize_for_comparison(first) - _resize_for_comparison(second))
    )
    return 1 - float(difference / 255)


def _best_crop_similarity(
    input_image_path: str | Path, candidate_image_path: str | Path
) -> float:
    """Compare a full image with plausible crops of the other image."""
    input_image = _grayscale_array(input_image_path)
    candidate_image = _grayscale_array(candidate_image_path)
    input_ratio = input_image.shape[1] / input_image.shape[0]
    candidate_ratio = candidate_image.shape[1] / candidate_image.shape[0]
    positions = (0, 0.25, 0.5, 0.75, 1)

    scores = [
        _visual_similarity(
            input_image,
            _crop_to_aspect_ratio(candidate_image, input_ratio, position),
        )
        for position in positions
    ]
    scores.extend(
        _visual_similarity(
            _crop_to_aspect_ratio(input_image, candidate_ratio, position),
            candidate_image,
        )
        for position in positions
    )
    return max(scores)


def compare_images(
    input_image_path: str | Path,
    candidate_image_path: str | Path,
    max_hash_distance: int = 40,
    max_aspect_ratio_delta: float = 0.08,
    min_crop_similarity: float = 0.82,
) -> ImageMatch:
    """Check whether a candidate is a duplicate, repost, or crop of the input."""
    input_hash, input_ratio = _difference_hash(input_image_path)
    candidate_hash, candidate_ratio = _difference_hash(candidate_image_path)

    hash_distance = (input_hash ^ candidate_hash).bit_count()
    aspect_ratio_delta = abs(input_ratio - candidate_ratio) / input_ratio
    direct_match = (
        hash_distance <= max_hash_distance
        and aspect_ratio_delta <= max_aspect_ratio_delta
    )
    crop_similarity = _best_crop_similarity(input_image_path, candidate_image_path)
    matches = direct_match or crop_similarity >= min_crop_similarity

    return ImageMatch(matches, hash_distance, aspect_ratio_delta, crop_similarity)
