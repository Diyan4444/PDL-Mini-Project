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

# Regex to detect major question boundaries (e.g. Q.1, Q.2, Q1, Q2, Question 3, 1., 2.)
MAJOR_QUESTION_PATTERN = re.compile(
    r"^(?:Q(?:uestion)?\s*[\.\:]?\s*(\d{1,2})|(\d{1,2})[\.\)])(?!\d)",
    re.IGNORECASE,
)

# Regex to extract marks (e.g. [5M], (5), [10 Marks], (4))
MARKS_PATTERN = re.compile(
    r"(?:\[|\()(?:\s*(\d{1,2})\s*(?:M|Marks|marks)?\s*)(?:\]|\))",
    re.IGNORECASE,
)

EXAM_INSTRUCTION_PATTERNS = [
    re.compile(r"all questions are compulsory", re.I),
    re.compile(r"all questions carry equal marks", re.I),
    re.compile(r"figures to the right indicate", re.I),
    re.compile(r"answers to individual question must be grouped", re.I),
    re.compile(r"non-programmable calculator", re.I),
    re.compile(r"programmable calculator", re.I),
    re.compile(r"assume suitable data", re.I),
    re.compile(r"draw neat sketches", re.I),
    re.compile(r"veermata|institute|university|department of", re.I),
]

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
    "numerical": ["numerical", "given that", "solve for", "assuming"],
}


def is_generic_instruction(text: str) -> bool:
    """Detects whether text is an exam administrative header instruction rather than an actual question."""
    t_clean = text.lower()
    return any(p.search(t_clean) for p in EXAM_INSTRUCTION_PATTERNS)


def remove_watermark_noise(raw_text: str) -> str:
    """Filters out repetitive background watermark strings and document headers."""
    cleaned_lines = []
    for line in raw_text.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        if re.match(r"^---\s*Page\s*\d+\s*---$", trimmed, re.IGNORECASE):
            continue
        tokens = [t.lower() for t in re.findall(r"\b[a-zA-Z]{3,}\b", trimmed)]
        if tokens:
            counts = Counter(tokens)
            most_common_word, freq = counts.most_common(1)[0]
            if freq >= 3 and (freq / len(tokens)) > 0.4:
                continue
        cleaned_lines.append(trimmed)
    return "\n".join(cleaned_lines)


def extract_marks_from_text(text: str, default_marks: float = 5.0) -> Tuple[float, bool]:
    """Extracts question marks using regular expressions."""
    matches = MARKS_PATTERN.findall(text)
    if matches:
        # Sum valid marks found across subquestions if multiple exist (e.g. (5) and (5) -> 10.0)
        valid_marks = [float(m) for m in matches if m and m.isdigit() and 1.0 <= float(m) <= 30.0]
        if valid_marks:
            # If multiple subquestion marks exist, return sum (capped at 25)
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
        score += 0.05  # Bonus for high-res visual crop availability

    return max(0.05, min(1.0, round(score, 2)))


def extract_page_question_blocks_with_crops(
    page_img: Image.Image,
    ocr_lines: List[Any],
    paper_id: int,
    page_idx: int,
) -> List[Dict[str, Any]]:
    """Extracts question blocks from a page, automatically clubbing subquestions
    (e.g., 1A, 1B, 1C) under parent Question Q.1, and crops a high-resolution visual
    snippet of the entire question block directly from the page image.
    
    This preserves math formulas, integrals, symbols, and schematics with 100% visual fidelity.
    """
    img_w, img_h = page_img.size
    
    # Sort detected lines strictly by vertical reading order (top Y coordinate)
    valid_items = []
    for item in ocr_lines:
        if not item or len(item) < 2:
            continue
        box = item[0]
        text = str(item[1]).strip()
        if not text or is_generic_instruction(text):
            continue
        
        # Check watermark token repetition
        tokens = [t.lower() for t in re.findall(r"\b[a-zA-Z]{3,}\b", text)]
        if tokens:
            counts = Counter(tokens)
            if counts.most_common(1)[0][1] >= 3 and (counts.most_common(1)[0][1] / len(tokens)) > 0.4:
                continue

        y_top = min(p[1] for p in box)
        y_bot = max(p[1] for p in box)
        valid_items.append({
            "text": text,
            "y_top": y_top,
            "y_bot": y_bot,
        })

    valid_items.sort(key=lambda x: x["y_top"])

    questions = []
    current_q: Optional[Dict[str, Any]] = None

    for item in valid_items:
        text = item["text"]
        match = MAJOR_QUESTION_PATTERN.match(text)

        if match:
            # 1. Close and crop accumulated previous question
            if current_q and current_q["lines"]:
                crop_path = _save_question_crop(page_img, current_q, paper_id, page_idx, img_w, img_h)
                current_q["image_path"] = crop_path
                questions.append(current_q)
                current_q = None

            # 2. Start new major question
            matched_num = match.group(1) or match.group(2) or match.group(0)
            cleaned_num = re.sub(r"[^\w]", "", matched_num)

            current_q = {
                "question_number": cleaned_num or str(len(questions) + 1),
                "lines": [text],
                "y_start": item["y_top"],
                "y_end": item["y_bot"],
            }
        else:
            # Subquestion or continuation line (e.g., subparts 1A, 1B, formulas, CO codes)
            if current_q is not None:
                current_q["lines"].append(text)
                current_q["y_end"] = max(current_q["y_end"], item["y_bot"])

    # 3. Close the final question block on this page
    if current_q and current_q["lines"]:
        crop_path = _save_question_crop(page_img, current_q, paper_id, page_idx, img_w, img_h)
        current_q["image_path"] = crop_path
        questions.append(current_q)

    # Clean text and combine marks for returned questions
    results = []
    for q in questions:
        combined_text = "\n".join(q["lines"]).strip()
        if len(combined_text) > 15:
            marks, marks_found = extract_marks_from_text(combined_text, default_marks=5.0)
            results.append({
                "question_number": q["question_number"],
                "question_text": combined_text,
                "image_path": q.get("image_path"),
                "marks": marks,
                "marks_found": marks_found,
            })

    return results


def _save_question_crop(
    page_img: Image.Image,
    q_data: Dict[str, Any],
    paper_id: int,
    page_idx: int,
    img_w: int,
    img_h: int,
) -> Optional[str]:
    """Crops a rectangular high-res visual snippet of the question block."""
    try:
        y1 = max(0, int(q_data["y_start"] - 14))
        y2 = min(img_h, int(q_data["y_end"] + 18))
        x1 = max(0, int(0.03 * img_w))
        x2 = min(img_w, int(0.97 * img_w))

        if (y2 - y1) >= 40:
            crop_img = page_img.crop((x1, y1, x2, y2))
            crop_filename = f"snippet_p{paper_id}_pg{page_idx+1}_q{q_data['question_number']}_{uuid.uuid4().hex[:6]}.png"
            dest_path = os.path.join(DIAGRAM_ASSETS_DIR, crop_filename)
            crop_img.save(dest_path, "PNG")
            return dest_path
    except Exception:
        pass
    return None
