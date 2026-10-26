import os
import uuid
from typing import Optional, Tuple
from PIL import Image
import imagehash
from modules.database import get_all_diagram_groups, add_diagram_group


def compute_image_phash(image_path: str) -> Optional[str]:
    """Computes a 64-bit Perceptual Hash (pHash) string for the given image file.
    
    Returns hex string representation or None if image cannot be parsed.
    """
    if not os.path.exists(image_path):
        return None
    try:
        with Image.open(image_path) as img:
            # Convert to RGB to handle alpha channels and palette images cleanly
            img_rgb = img.convert("RGB")
            h = imagehash.phash(img_rgb)
            return str(h)
    except Exception:
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
