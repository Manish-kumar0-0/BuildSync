from dataclasses import dataclass
from pathlib import Path

import numpy as np


class OpenCVImageError(ValueError):
    """A safe image validation or preprocessing error."""


@dataclass(frozen=True)
class PreparedImage:
    path: Path
    image: np.ndarray
    width: int
    height: int


SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_DIMENSION = 8192


def load_and_prepare(path: Path) -> PreparedImage:
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise OpenCVImageError("Only JPEG, PNG, and WebP images are supported")
    if not path.is_file():
        raise OpenCVImageError("Evidence image is unavailable")
    try:
        import cv2

        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    except (OSError, ImportError) as exc:
        raise OpenCVImageError("OpenCV image processing is unavailable") from exc
    if image is None:
        raise OpenCVImageError("Evidence image is unreadable or corrupted")
    height, width = image.shape[:2]
    if width < 2 or height < 2 or width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise OpenCVImageError("Evidence image dimensions are not supported")
    return PreparedImage(path=path, image=image, width=width, height=height)


def normalized_image(prepared: PreparedImage, max_dimension: int = 2048) -> np.ndarray:
    import cv2

    image = prepared.image
    scale = min(1.0, max_dimension / max(image.shape[0], image.shape[1]))
    if scale < 1:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)


def image_difference(previous: PreparedImage, current: PreparedImage) -> dict[str, float | int]:
    import cv2

    target_size = (min(previous.width, current.width), min(previous.height, current.height))
    if target_size[0] < 2 or target_size[1] < 2:
        raise OpenCVImageError("Evidence images are too small to compare")
    previous_gray = cv2.cvtColor(previous.image, cv2.COLOR_BGR2GRAY)
    current_gray = cv2.cvtColor(current.image, cv2.COLOR_BGR2GRAY)
    previous_gray = cv2.resize(previous_gray, target_size, interpolation=cv2.INTER_AREA)
    current_gray = cv2.resize(current_gray, target_size, interpolation=cv2.INTER_AREA)
    previous_gray = cv2.GaussianBlur(previous_gray, (5, 5), 0)
    current_gray = cv2.GaussianBlur(current_gray, (5, 5), 0)
    difference = cv2.absdiff(previous_gray, current_gray)
    _, changed = cv2.threshold(difference, 30, 255, cv2.THRESH_BINARY)
    changed_pixels = int(cv2.countNonZero(changed))
    total_pixels = int(changed.shape[0] * changed.shape[1])
    return {
        "width": target_size[0],
        "height": target_size[1],
        "changed_pixels": changed_pixels,
        "changed_ratio": round(changed_pixels / total_pixels, 6),
        "method": "aligned_resized_grayscale_blurred_difference",
    }
