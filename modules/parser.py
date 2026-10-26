import os
import re
import uuid
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple
import pymupdf as fitz
from PIL import Image

DIAGRAM_ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "diagrams"
)
os.makedirs(DIAGRAM_ASSETS_DIR, exist_ok=True)

# Regex to detect major question boundaries strictly starting with Q or Question
# (e.g., Q.1, Q. 1, Q1, Q-1, Question 1, Q.2, Q.3, Q.4, Q.3a.)
MAJOR_QUESTION_PATTERN = re.compile(
    r"^(?:Q(?:uestion)?\s*[\.\:\-\)]?\s*(\d{1,2}))",
    re.IGNORECASE,
)

# Regex to extract marks (e.g. [5M], (5), [10 Marks], (4))
MARKS_PATTERN = re.compile(
    r"(?:\[|\()(?:\s*(\d{1,2})\s*(?:M|Marks|marks)?\s*)(?:\]|\))",
    re.IGNORECASE,
)

TAG_KEYWORDS = {
    "draw": ["draw", "sketch", "plot", "illustrate"],
    "diagram": ["diagram", "schematic", "circuit", "flowchart"],
    "graph": ["graph", "waveform", "timing chart"],
    "derive": ["derive", "derivation", "mathematical proof", "show that", "prove that"],
    "calculate": ["calculate", "compute", "determine the value", "find the", "evaluate"],
    "explain": ["explain", "describe", "elaborate", "discuss"],
    "define": ["define", "state the", "what is", "meaning of"],
    "differentiate": ["differentiate", "distinguish", "contrast", "difference between", "compare"],
    "code": ["write a python", "program", "pseudo-code", "algorithm", "def ", "function"],
    "architecture": ["architecture", "block diagram", "pipeline", "subsystem"],
    "short-note": ["short note", "write notes on", "briefly explain"],
    "numerical": ["numerical", "given that", "solve for", "assuming", "integral", "matrix"],
}


def extract_marks_from_text(text: str, default_marks: float = 5.0) -> Tuple[float, bool]:
    """Extracts question marks, summing across subquestions if multiple exist."""
    matches = MARKS_PATTERN.findall(text)
    if matches:
        valid_marks = [float(m) for m in matches if m and m.isdigit() and 1.0 <= float(m) <= 30.0]
        if valid_marks:
            total = sum(valid_marks)
            return min(30.0, total), True
    return default_marks, False


def suggest_tags_from_text(text: str) -> List[str]:
    """Infers standard tags based on rule-based keyword matching."""
    text_lower = text.lower()
    inferred_tags = []
    for tag_name, keywords in TAG_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            inferred_tags.append(tag_name)
    return inferred_tags


def calculate_confidence_score(
    text: str,
    marks_found: bool,
    is_ocr: bool,
    has_snippet: bool
) -> float:
    """Calculates extraction confidence score from 0.0 to 1.0."""
    score = 1.0
    text_len = len(text.strip())

    if not marks_found:
        score -= 0.15
    if text_len < 25:
        score -= 0.30
    elif text_len < 50:
        score -= 0.10
    if is_ocr:
        score -= 0.10
    if has_snippet:
        score += 0.05

    return max(0.05, min(1.0, round(score, 2)))


def extract_page_question_blocks_with_crops(
    page_img: Image.Image,
    ocr_lines: List[Any],
    paper_id: int,
    page_idx: int,
) -> List[Dict[str, Any]]:
    """Extracts question blocks from a page, strictly isolating questions from the document
    header and instructions box. Automatically clubs subquestions (1A+1B+1C) into the parent question,
    sums their marks, and crops a high-resolution snippet of the exact question region.
    """
    img_w, img_h = page_img.size

    # 1. Clean items: ignore watermark noise and stop at END OF PAPER
    clean_items = []
    for item in (ocr_lines or []):
        if not item or len(item) < 2:
            continue
        text = str(item[1]).strip()
        if not text:
            continue
        if re.search(r"end of paper", text, re.I):
            break

        # Filter out repetitive watermark noise
        tokens = [t.lower() for t in re.findall(r"\b[a-zA-Z]{3,}\b", text)]
        if tokens:
            counts = Counter(tokens)
            if counts.most_common(1)[0][1] >= 3 and (counts.most_common(1)[0][1] / len(tokens)) > 0.4:
                continue
        clean_items.append(item)

    if not clean_items:
        return []

    # 2. Identify indices where major questions start (Q.1, Q.2, Q.3, etc.)
    q_indices = []
    for idx, item in enumerate(clean_items):
        text = str(item[1]).strip()
        m = MAJOR_QUESTION_PATTERN.match(text)
        if m:
            q_num = m.group(1)
            q_indices.append((idx, q_num, text))

    # If no major question boundary exists on this page, discard entire page content (it is cover/header/instructions)
    if not q_indices:
        return []

    results = []

    # 3. Process each question block: all lines between Q[k] and Q[k+1] are clubbed
    for k in range(len(q_indices)):
        start_idx, q_num, _ = q_indices[k]
        end_idx = q_indices[k + 1][0] if k + 1 < len(q_indices) else len(clean_items)

        q_block_items = clean_items[start_idx:end_idx]
        if not q_block_items:
            continue

        # Vertical pixel boundaries
        y_min = min(item[0][0][1] for item in q_block_items)
        y_max = max(item[0][2][1] for item in q_block_items)

        # Clubbed text across subquestions
        block_text = " ".join(str(item[1]).strip() for item in q_block_items)
        marks, marks_found = extract_marks_from_text(block_text, default_marks=5.0)

        # Crop high-resolution visual snippet excluding document headers and instructions
        y1 = max(0, int(y_min - 12))
        y2 = min(img_h, int(y_max + 14))
        x1 = max(0, int(0.04 * img_w))
        x2 = min(img_w, int(0.96 * img_w))

        crop_path = None
        if (y2 - y1) >= 40:
            crop_filename = f"snippet_p{paper_id}_pg{page_idx+1}_q{q_num}_{uuid.uuid4().hex[:6]}.png"
            dest_path = os.path.join(DIAGRAM_ASSETS_DIR, crop_filename)
            crop_img = page_img.crop((x1, y1, x2, y2))
            crop_img.save(dest_path, "PNG")
            crop_path = dest_path

        results.append({
            "question_number": q_num,
            "question_text": block_text,
            "image_path": crop_path,
            "marks": marks,
            "marks_found": marks_found,
        })

    return results
