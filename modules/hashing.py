import os
import uuid
from typing import Any, Optional, Tuple, Union
import numpy as np
from PIL import Image
import imagehash
from modules.database import get_all_diagram_groups, add_diagram_group


def compute_image_phash(image_input: Union[str, np.ndarray, Image.Image]) -> Optional[str]:
    """Computes a 64-bit Perceptual Hash (pHash) string for the given image.
    
    Accepts a file path string, a numpy BGR/RGB array, or a PIL Image instance.
    Returns hex string representation or None if image cannot be parsed.
    """
    if image_input is None:
        return None
    try:
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                return None
            with Image.open(image_input) as img:
                return str(imagehash.phash(img.convert("RGB")))
        elif isinstance(image_input, np.ndarray):
            if image_input.size == 0:
                return None
            # If 3 channels (BGR from OpenCV), convert to RGB
            if len(image_input.shape) == 3 and image_input.shape[2] == 3:
                rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB) if 'cv2' in globals() else image_input[:, :, ::-1]
                pil_img = Image.fromarray(rgb)
            else:
                pil_img = Image.fromarray(image_input)
            return str(imagehash.phash(pil_img.convert("RGB")))
        elif isinstance(image_input, Image.Image):
            return str(imagehash.phash(image_input.convert("RGB")))
    except Exception as e:
        return None
    return None


def calculate_hamming_distance(hash1_str: str, hash2_str: str) -> int:
    """Calculates the Hamming bit distance between two hexadecimal perceptual hash strings."""
    try:
        h1 = imagehash.hex_to_hash(hash1_str)
        h2 = imagehash.hex_to_hash(hash2_str)
        return int(h1 - h2)
    except Exception:
        return 999


def find_or_create_diagram_group(image_phash: str, max_hamming_distance: int = 5) -> Tuple[int, str, bool]:
    """Matches an image pHash against stored diagram groups.
    
    If Hamming distance <= max_hamming_distance, assigns to existing group.
    Otherwise, creates and commits a new diagram group.
    
    Returns:
        (diagram_group_id, group_uid, is_new_group)
    """
    if not image_phash:
        return 0, "", False

    existing_groups = get_all_diagram_groups()
    best_match_id = None
    best_match_uid = ""
    min_dist = 999

    for grp in existing_groups:
        rep_hash = grp.get("representative_phash", "")
        dist = calculate_hamming_distance(image_phash, rep_hash)
        if dist <= max_hamming_distance and dist < min_dist:
            min_dist = dist
            best_match_id = grp["id"]
            best_match_uid = grp["group_uid"]

    if best_match_id is not None:
        return best_match_id, best_match_uid, False

    # Create new group
    new_uid = f"DIAG_{uuid.uuid4().hex[:8].upper()}"
    new_id = add_diagram_group(new_uid, image_phash)
    return new_id, new_uid, True
