import os
import cv2
import numpy as np

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def validate_file_type(file_path):
    """
    Checks the file has a valid image extension before any processing runs.
    Returns a dict: {"valid": bool, "reason": str or None}
    """
    _, ext = os.path.splitext(file_path.lower())
    if ext not in ALLOWED_EXTENSIONS:
        return {"valid": False, "reason": f"Unsupported file type: '{ext}'. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}
    return {"valid": True, "reason": None}


def check_image_quality(image_path, blur_threshold=50.0, min_resolution=(150, 150)):
    """
    Checks if an image is likely too blurry or too low-resolution for reliable OCR.
    Returns a dict: {"acceptable": bool, "reason": str or None, "blur_score": float}
    """
    image = cv2.imread(image_path)

    if image is None:
        return {"acceptable": False, "reason": "Could not read image file", "blur_score": None}

    height, width = image.shape[:2]
    if width < min_resolution[0] or height < min_resolution[1]:
        return {
            "acceptable": False,
            "reason": f"Image resolution too low ({width}x{height}), minimum is {min_resolution[0]}x{min_resolution[1]}",
            "blur_score": None,
        }

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

    if blur_score < blur_threshold:
        return {
            "acceptable": False,
            "reason": f"Image appears too blurry (sharpness score: {blur_score:.1f}, minimum: {blur_threshold})",
            "blur_score": blur_score,
        }

    return {"acceptable": True, "reason": None, "blur_score": blur_score}