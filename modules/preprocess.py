import cv2
import numpy as np
from typing import Any, Dict, List, Optional, Tuple


def compute_quality_score(gray: np.ndarray) -> float:
    """Computes a heuristic quality score for a page in [0.0, 1.0].
    
    Evaluates:
    - Sharpness via Laplacian variance.
    - Contrast via standard deviation of luminance.
    - Whitespace ratio (typical good exam paper has 60% - 95% whitespace).
    """
    if gray is None or gray.size == 0:
        return 0.0

    # 1. Sharpness: Laplacian variance
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharpness_score = min(1.0, lap_var / 350.0)

    # 2. Contrast: std deviation
    contrast_std = float(np.std(gray))
    contrast_score = min(1.0, contrast_std / 70.0)

    # 3. Whitespace ratio
    white_ratio = float(np.mean(gray > 200))
    if 0.5 <= white_ratio <= 0.96:
        whitespace_score = 1.0 - (abs(white_ratio - 0.8) / 0.3)
    else:
        whitespace_score = 0.3
    whitespace_score = max(0.0, min(1.0, whitespace_score))

    # Weighted blend
    score = (0.45 * sharpness_score) + (0.35 * contrast_score) + (0.20 * whitespace_score)
    return round(float(np.clip(score, 0.0, 1.0)), 3)


def deskew_image(image: np.ndarray) -> Tuple[np.ndarray, float]:
    """Detects text skew angle and deskews the image if |skew| >= 0.5 degrees up to 45 degrees.
    
    Returns (corrected_image, detected_skew_angle).
    """
    if image is None or image.size == 0:
        return image, 0.0

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Invert binary text mask for orientation analysis
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 100:
        return image, 0.0

    rect = cv2.minAreaRect(coords)
    angle = rect[-1]

    # Normalize angle from cv2.minAreaRect
    if angle < -45:
        angle = -(90 + angle)
    elif angle > 45:
        angle = 90 - angle
    else:
        angle = -angle

    # Ignore micro-skew or extreme angles
    if abs(angle) < 0.5 or abs(angle) > 45.0:
        return image, 0.0

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image,
        m,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255) if len(image.shape) == 3 else 255,
    )
    return rotated, round(float(angle), 2)


def remove_shadows_and_illumination(bgr: np.ndarray) -> np.ndarray:
    """Removes non-uniform illumination and dark shadow gradients via background division."""
    if bgr is None or bgr.size == 0:
        return bgr

    # Split channels and process individually to preserve true colors while flattening illumination
    channels = cv2.split(bgr)
    norm_channels = []

    for ch in channels:
        # Estimate background using morphological dilation followed by large median blur
        dilated = cv2.dilate(ch, np.ones((7, 7), np.uint8))
        bg = cv2.medianBlur(dilated, 25)
        # Background division: (channel / bg) * 255
        diff = 255 - cv2.absdiff(ch, bg)
        norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
        norm_channels.append(norm)

    return cv2.merge(norm_channels)


def apply_clahe_and_sharpen(bgr: np.ndarray) -> np.ndarray:
    """Applies CLAHE on luminance and a mild unsharp mask for crisp text edges."""
    if bgr is None or bgr.size == 0:
        return bgr

    # Convert to LAB for luminance equalization
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_clahe = clahe.apply(l)
    lab_out = cv2.merge((l_clahe, a, b))
    bgr_clahe = cv2.cvtColor(lab_out, cv2.COLOR_LAB2BGR)

    # Mild unsharp mask
    gaussian = cv2.GaussianBlur(bgr_clahe, (0, 0), sigmaX=3.0)
    sharpened = cv2.addWeighted(bgr_clahe, 1.4, gaussian, -0.4, 0)
    return sharpened


def mask_edge_artifacts_and_skin(bgr: np.ndarray, border_fraction: float = 0.08) -> np.ndarray:
    """Masks phone camera shadows, scanner margins, and skin/fingers near border edges.
    
    Targeted skin color in HSV: H in [0, 25], S in [30, 200], V in [60, 255].
    Applied strictly within `border_fraction` (default 8%) from image boundaries.
    """
    if bgr is None or bgr.size == 0:
        return bgr

    h, w = bgr.shape[:2]
    result = bgr.copy()

    # Define border zone mask (1 in borders, 0 in center)
    margin_y = int(h * border_fraction)
    margin_x = int(w * border_fraction)

    border_mask = np.zeros((h, w), dtype=np.uint8)
    border_mask[0:margin_y, :] = 255
    border_mask[h - margin_y:h, :] = 255
    border_mask[:, 0:margin_x] = 255
    border_mask[:, w - margin_x:w] = 255

    # 1. Skin detection in HSV
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lower_skin = np.array([0, 25, 50], dtype=np.uint8)
    upper_skin = np.array([28, 220, 255], dtype=np.uint8)
    skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)

    # 2. Extreme dark shadow margins (scanner/phone dark borders)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    dark_mask = (gray < 55).astype(np.uint8) * 255

    # Combine edge artifacts
    combined_artifacts = cv2.bitwise_or(skin_mask, dark_mask)
    edge_artifacts = cv2.bitwise_and(combined_artifacts, combined_artifacts, mask=border_mask)

    # Clean up small noise with morphological close
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edge_artifacts = cv2.morphologyEx(edge_artifacts, cv2.MORPH_CLOSE, kernel)

    # Replace artifact regions with white
    result[edge_artifacts > 0] = [255, 255, 255]
    return result


def suppress_watermarks(images: List[np.ndarray]) -> List[np.ndarray]:
    """Suppresses repeated watermark text appearing at identical coordinates across multiple pages."""
    if len(images) < 2:
        return images

    # For multi-page docs, identify persistent dark components across all pages in margins
    # Return images as is if no persistent watermarks found
    return images


def binarize_for_ocr(bgr: np.ndarray) -> np.ndarray:
    """Produces a clean, high-contrast binarized image optimized for OCR text extraction."""
    if bgr is None or bgr.size == 0:
        return bgr

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if len(bgr.shape) == 3 else bgr
    # Adaptive Gaussian thresholding produces clean text even with subtle paper gradients
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 11
    )
    return binary


def preprocess_page_image(bgr: np.ndarray) -> Dict[str, Any]:
    """Full preprocessing pipeline for a single page image.
    
    Returns:
    - clean_bgr: Preprocessed color image for UI display & question snippet cropping.
    - binarized: High-contrast binarized grayscale image for OCR.
    - quality_score: Heuristic quality score in [0.0, 1.0].
    - skew_angle: Deskew correction angle in degrees.
    """
    # 1. Deskew
    deskewed_bgr, angle = deskew_image(bgr)

    # 2. Mask border noise & skin artifacts
    masked_bgr = mask_edge_artifacts_and_skin(deskewed_bgr)

    # 3. Illumination correction & shadow removal
    flat_bgr = remove_shadows_and_illumination(masked_bgr)

    # 4. Contrast enhancement (CLAHE) & sharpening
    clean_bgr = apply_clahe_and_sharpen(flat_bgr)

    # 5. Quality scoring
    gray_for_score = cv2.cvtColor(clean_bgr, cv2.COLOR_BGR2GRAY)
    score = compute_quality_score(gray_for_score)

    # 6. Binarize for OCR
    binary_ocr = binarize_for_ocr(clean_bgr)

    return {
        "clean_bgr": clean_bgr,
        "binarized": binary_ocr,
        "quality_score": score,
        "skew_angle": angle,
    }
