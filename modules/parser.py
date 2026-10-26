import os
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
import pymupdf as fitz
from PIL import Image

DIAGRAM_ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "diagrams"
)
os.makedirs(DIAGRAM_ASSETS_DIR, exist_ok=True)

# Regex pattern for splitting questions
QUESTION_BOUNDARY_PATTERN = re.compile(
    r"(?m)^(?:Q(?:uestion)?\s*(\d{1,2})[\.\:\)]|(\d{1,2})[\.\:\)]\s*(?:\([a-eA-E]\))?|(?:\([a-eA-E]\)))\s+",
    re.IGNORECASE,
)

# Regex pattern for extracting marks
MARKS_PATTERN = re.compile(
    r"(?:\[|\()(?:\s*(\d{1,2})\s*(?:M|Marks|marks)?\s*)(?:\]|\))",
    re.IGNORECASE,
)

# Keywords for rule-based automatic tagging
TAG_KEYWORDS = {
    "draw": ["draw", "sketch", "plot", "illustrate"],
    "diagram": ["diagram", "schematic", "circuit", "flowchart"],
    "graph": ["graph", "waveform", "timing chart"],
    "derive": ["derive", "derivation", "mathematical proof", "show that"],
    "calculate": ["calculate", "compute", "determine the value", "find the"],
    "explain": ["explain", "describe", "elaborate", "discuss"],
    "define": ["define", "state the", "what is", "meaning of"],
    "differentiate": ["differentiate", "distinguish", "contrast", "difference between", "compare"],
    "code": ["write a python", "program", "pseudo-code", "algorithm", "def ", "function"],
    "architecture": ["architecture", "block diagram", "pipeline", "subsystem"],
    "short-note": ["short note", "write notes on", "briefly explain"],
    "numerical": ["numerical", "given that", "solve for", "assuming"],
}


def extract_marks_from_text(text: str, default_marks: float = 5.0) -> Tuple[float, bool]:
    """Extracts question marks using regular expressions.
    
    Returns (marks, is_explicitly_found).
    """
    matches = MARKS_PATTERN.findall(text)
    if matches:
        for m in reversed(matches):
            if m and m.isdigit():
                val = float(m)
                if 1.0 <= val <= 30.0:
                    return val, True
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
    has_diagram: bool
) -> float:
    """Calculates extraction confidence score from 0.0 to 1.0.
    
    Applies strict penalties for missing metadata, OCR ambiguity, or short text.
    """
    score = 1.0
    text_len = len(text.strip())

    if not marks_found:
        score -= 0.20
    if text_len < 20:
        score -= 0.35
    elif text_len < 40:
        score -= 0.15
    if is_ocr:
        score -= 0.20
    if has_diagram and text_len < 15:
        score -= 0.10

    return max(0.05, min(1.0, round(score, 2)))


def crop_page_images(page: fitz.Page, paper_id: int, page_idx: int) -> List[Dict[str, Any]]:
    """Extracts and crops raster images & embedded figures from a PDF page.
    
    Filters out miniature icons and headers (< 60x60 pixels).
    """
    cropped_visuals = []
    image_list = page.get_images(full=True)

    for img_idx, img_info in enumerate(image_list):
        xref = img_info[0]
        base_image = page.parent.extract_image(xref)
        image_bytes = base_image["image"]
        image_ext = base_image["ext"]
        width = base_image["width"]
        height = base_image["height"]

        if width >= 60 and height >= 60:
            unique_filename = f"crop_p{paper_id}_pg{page_idx+1}_i{img_idx}_{uuid.uuid4().hex[:6]}.png"
            dest_path = os.path.join(DIAGRAM_ASSETS_DIR, unique_filename)
            
            with open(dest_path, "wb") as f:
                f.write(image_bytes)
            
            cropped_visuals.append({
                "path": dest_path,
                "width": width,
                "height": height,
                "xref": xref,
            })

    return cropped_visuals


def split_text_into_questions(raw_text: str) -> List[Dict[str, Any]]:
    """Splits full document or page text stream into discrete question blocks."""
    lines = raw_text.splitlines()
    questions = []
    current_q_num = "1"
    current_lines = []

    for line in lines:
        match = QUESTION_BOUNDARY_PATTERN.match(line.strip())
        if match:
            # Commit accumulated previous question
            if current_lines:
                combined_text = "\n".join(current_lines).strip()
                if len(combined_text) > 10:
                    questions.append({
                        "question_number": current_q_num,
                        "question_text": combined_text,
                    })
                current_lines = []
            
            # Determine new question label
            matched_num = match.group(1) or match.group(2) or match.group(0).strip(".:() ")
            current_q_num = matched_num if matched_num else str(len(questions) + 1)
            # Remove header from line text
            remaining_text = QUESTION_BOUNDARY_PATTERN.sub("", line, count=1).strip()
            if remaining_text:
                current_lines.append(remaining_text)
        else:
            if line.strip():
                current_lines.append(line.strip())

    # Flush final accumulated question
    if current_lines:
        combined_text = "\n".join(current_lines).strip()
        if len(combined_text) > 10:
            questions.append({
                "question_number": current_q_num,
                "question_text": combined_text,
            })

    # If regex did not find multiple questions, return the entire block as question 1
    if not questions and len(raw_text.strip()) > 15:
        questions.append({
            "question_number": "1",
            "question_text": raw_text.strip(),
        })

    return questions
