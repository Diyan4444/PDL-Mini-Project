import hashlib
import os
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

from modules.hashing import compute_image_phash

DIAGRAM_ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "diagrams"
)
os.makedirs(DIAGRAM_ASSETS_DIR, exist_ok=True)

# Master directive: store each sub-question as an individual row
SPLIT_SUBQUESTIONS = True

MAJOR_Q_PATTERN = re.compile(
    r"^(?:Q(?:uestion)?\s*[\.\:\-\)]?\s*(\d{1,2}))",
    re.IGNORECASE,
)

SUB_PART_PATTERN = re.compile(
    r"^(?:[\(\[]?\s*([a-dA-D])\s*[\)\]\.\:]|\b([a-dA-D])\s*[\)\.\:])\s*(.*)",
    re.IGNORECASE,
)

TAG_KEYWORDS = {
    "draw": ["draw", "sketch", "plot", "illustrate"],
    "diagram": ["diagram", "schematic", "circuit", "flowchart"],
    "graph": ["graph", "waveform", "timing chart", "directed graph", "kruskal", "prim", "dijkstra", "spanning tree", "shortest path"],
    "derive": ["derive", "derivation", "mathematical proof", "show that", "prove that"],
    "calculate": ["calculate", "compute", "determine the value", "find the", "evaluate"],
    "explain": ["explain", "describe", "elaborate", "discuss", "state"],
    "define": ["define", "state the", "what is", "meaning of"],
    "differentiate": ["differentiate", "distinguish", "contrast", "difference between", "compare"],
    "code": ["write a python", "program", "pseudo-code", "algorithm", "def ", "function"],
    "architecture": ["architecture", "block diagram", "pipeline", "subsystem"],
    "short-note": ["short note", "write notes on", "briefly explain"],
    "numerical": ["numerical", "given that", "solve for", "assuming", "integral", "matrix", "recurrence", "eigenvalue", "linear equation"],
}


def parse_marks_and_co(text: str) -> Tuple[float, Optional[str], bool]:
    """Extracts numerical marks and Course Outcome (CO) tag with OCR error resilience."""
    co_tag = None
    marks = 5.0
    marks_found = False

    # 1. Extract CO tag (CO1..CO12, tolerating C0 with zero)
    co_match = re.search(r"(?:\[|\(|\b)(?:CO|C0)\s*(\d{1,2})(?:\]|\)|\b)", text, re.IGNORECASE)
    if co_match:
        co_tag = f"CO{co_match.group(1)}"

    # 2. Extract Marks
    clean_text = text
    if co_match:
        clean_text = clean_text[:co_match.start()] + " " + clean_text[co_match.end():]

    # Handle OCR confusion: [s] or [S] -> 5
    clean_text = re.sub(r"\[[sS]\]", "[5]", clean_text)
    clean_text = re.sub(r"\|", " ", clean_text)

    m_marks = re.findall(r"(?:\[|\()(?:\s*(\d{1,2})\s*(?:M|Marks|marks)?\s*)(?:\]|\))", clean_text, re.IGNORECASE)
    if m_marks:
        val = float(m_marks[-1])
        if 1.0 <= val <= 30.0:
            marks = val
            marks_found = True
    else:
        m_bare = re.search(r"\b(\d{1,2})\s*(?:M|Marks|marks)\b", clean_text, re.IGNORECASE)
        if m_bare:
            val = float(m_bare.group(1))
            if 1.0 <= val <= 30.0:
                marks = val
                marks_found = True

    return marks, co_tag, marks_found


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
    has_snippet: bool,
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


def detect_isolated_figures(
    clean_bgr: np.ndarray,
    ocr_boxes: List[Any],
    y_min: int,
    y_max: int,
) -> List[Dict[str, Any]]:
    """Detects isolated non-text diagram/graph components within a given vertical band."""
    h_img, w_img = clean_bgr.shape[:2]
    band_y1 = max(0, y_min)
    band_y2 = min(h_img, y_max)
    
    if band_y2 - band_y1 < 35:
        return []

    band_bgr = clean_bgr[band_y1:band_y2, :]
    gray = cv2.cvtColor(band_bgr, cv2.COLOR_BGR2GRAY)
    
    # Binarize ink: dark ink on light background
    _, ink_mask = cv2.threshold(gray, 215, 255, cv2.THRESH_BINARY_INV)

    # Mask out all OCR text boxes that fall into this band
    for item in ocr_boxes:
        box = item[0]
        box_y1 = int(min(pt[1] for pt in box)) - band_y1
        box_y2 = int(max(pt[1] for pt in box)) - band_y1
        box_x1 = int(min(pt[0] for pt in box))
        box_x2 = int(max(pt[0] for pt in box))

        if box_y2 > 0 and box_y1 < (band_y2 - band_y1):
            pad = 6
            bx1 = max(0, box_x1 - pad)
            by1 = max(0, box_y1 - pad)
            bx2 = min(w_img, box_x2 + pad)
            by2 = min(band_y2 - band_y1, box_y2 + pad)
            ink_mask[by1:by2, bx1:bx2] = 0

    # Mask horizontal & vertical grid lines
    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(w_img * 0.25), 1))
    horiz_lines = cv2.morphologyEx(ink_mask, cv2.MORPH_OPEN, horiz_kernel)
    ink_mask[horiz_lines > 0] = 0

    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, int((band_y2 - band_y1) * 0.4)))
    vert_lines = cv2.morphologyEx(ink_mask, cv2.MORPH_OPEN, vert_kernel)
    ink_mask[vert_lines > 0] = 0

    # Find connected components of diagrams / graphs
    contours, _ = cv2.findContours(ink_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    figures = []

    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        # Only retain substantial visual components (diagrams, graphs, matrices)
        if w >= 50 and h >= 50 and area >= 2500:
            abs_y1 = band_y1 + max(0, y - 6)
            abs_y2 = band_y1 + min(band_y2 - band_y1, y + h + 6)
            abs_x1 = max(0, x - 6)
            abs_x2 = min(w_img, x + w + 6)

            fig_crop = clean_bgr[abs_y1:abs_y2, abs_x1:abs_x2]
            if fig_crop.size > 0:
                fig_hash = compute_image_phash(fig_crop)
                fig_filename = f"fig_{fig_hash[:12]}_{uuid.uuid4().hex[:4]}.png"
                fig_path = os.path.join(DIAGRAM_ASSETS_DIR, fig_filename)
                cv2.imwrite(fig_path, fig_crop)

                figures.append({
                    "path": fig_path,
                    "phash": fig_hash,
                    "bbox": (abs_x1, abs_y1, abs_x2, abs_y2),
                })

    return figures


def parse_page_questions(
    page_img_bgr: np.ndarray,
    ocr_lines: List[Any],
    paper_id: int,
    page_no: int,
    carry_parent_num: Optional[int] = None,
    open_question_from_prev_page: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], int]:
    """Parses questions on a single page, supporting:
    - Both Table layout (via column marks / CO delimiters) and Prefixed Q anchors.
    - Sub-question splitting (SPLIT_SUBQUESTIONS = True).
    - Inter-page continuation resolution (e.g. DAA Q3a graph at top of Page 2).
    - Diagram/graph extraction and perceptual hashing.
    - High-res question snippet cropping.
    """
    h_img, w_img = page_img_bgr.shape[:2]

    # 1. Clean OCR lines & detect layout signals
    clean_items = []
    is_table_layout = False

    for item in (ocr_lines or []):
        if not item or len(item) < 2:
            continue
        text = str(item[1]).strip()
        if not text:
            continue
        if re.search(r"\b(?:end\s+of\s+paper|all\s*the\s*best)\b", text, re.I):
            break

        if re.search(r"\b(?:Q\.?\s*Nos?|Questions|Marks)\b", text, re.I):
            is_table_layout = True

        # Mask margin watermarks (e.g. DAKSH GOHIL along leftmost margin)
        box = item[0]
        x_min = min(pt[0] for pt in box)
        if x_min < (0.07 * w_img) and re.search(r"DAKSH|GOHIL", text, re.I):
            continue

        clean_items.append(item)

    if not clean_items:
        return [], open_question_from_prev_page, carry_parent_num or 1

    clean_items.sort(key=lambda it: min(pt[1] for pt in it[0]))

    # Exclude institutional header lines
    header_cutoff_idx = 0
    for idx, it in enumerate(clean_items):
        t = str(it[1]).strip()
        if re.search(r"\b(?:Q\.?\s*Nos?|Questions|Instructions\s*1\.)\b", t, re.I):
            header_cutoff_idx = idx + 1
            is_table_layout = True
            break
        elif re.search(r"\b(?:Course\s*Name|Autonomous\s*Institute|Time\s*Allowed)\b", t, re.I):
            header_cutoff_idx = idx + 1

    content_items = clean_items[header_cutoff_idx:]
    if not content_items:
        content_items = clean_items

    # 2. Identify Anchors / Row Delimiters
    # In table layout, rows are delineated by:
    # - Question number/sub-letter on the left, OR
    # - Marks / CO badges on the right ([CO1] [5], [CO2] [7], etc.)
    row_delimiters = []
    curr_parent = carry_parent_num or 1

    for idx, it in enumerate(content_items):
        text = str(it[1]).strip()
        box = it[0]
        x_min = min(pt[0] for pt in box)
        y_min = min(pt[1] for pt in box)

        # Skip column header labels
        if re.search(r"^(?:Questions|Marks|Q\.?\s*Nos?|CO\d?)$", text, re.I):
            continue

        # A) Explicit Major Question anchor: Q.1, Q.2, Q.3, Q.4
        m_major = MAJOR_Q_PATTERN.match(text)
        if m_major:
            p_num = int(m_major.group(1))
            curr_parent = p_num
            m_sub = re.search(r"Q(?:uestion)?\s*[\.\:\-\)]?\s*\d{1,2}\s*[\.\:\-\)]?\s*([a-dA-D])[\.\)\:]", text)
            p_label = m_sub.group(1).lower() if m_sub else "a"
            row_delimiters.append({
                "item_idx": idx,
                "parent_num": p_num,
                "part_label": p_label,
                "y_min": y_min,
                "anchor_type": "explicit",
            })
            continue

        # B) Sub-letter anchor: a., b., c., (a), (b)
        m_sub_only = SUB_PART_PATTERN.match(text)
        if m_sub_only:
            sub_lbl = (m_sub_only.group(1) or m_sub_only.group(2)).lower()
            row_delimiters.append({
                "item_idx": idx,
                "parent_num": curr_parent,
                "part_label": sub_lbl,
                "y_min": y_min,
                "anchor_type": "explicit",
            })
            continue

        # C) Bare question number on left: 1, 2, 3
        if x_min < (0.22 * w_img) and re.match(r"^(\d{1,2})$", text):
            p_num = int(text)
            curr_parent = p_num
            row_delimiters.append({
                "item_idx": idx,
                "parent_num": p_num,
                "part_label": "a",
                "y_min": y_min,
                "anchor_type": "explicit",
            })
            continue

        # D) In Table Layout: Right-column Marks & CO tag anchor
        # (e.g. [CO1] [5], [CO2] [7], [C02] [8], [C04] [5])
        if is_table_layout or x_min > (0.65 * w_img):
            _, co_found, marks_found = parse_marks_and_co(text)
            if marks_found and (co_found or re.search(r"\[\d{1,2}\]", text)):
                row_delimiters.append({
                    "item_idx": idx,
                    "parent_num": curr_parent,
                    "part_label": None,
                    "y_min": y_min,
                    "anchor_type": "marks_anchor",
                })

    # If row delimiters were found only via marks or mixed, harmonize them into rows
    # Sort delimiters by y_min
    row_delimiters.sort(key=lambda d: d["y_min"])

    # Merge delimiters that belong to the exact same vertical line (within 20 px)
    merged_delims = []
    for d in row_delimiters:
        if merged_delims and abs(d["y_min"] - merged_delims[-1]["y_min"]) < 25:
            # If current has explicit anchor, upgrade the previous
            if d["anchor_type"] == "explicit":
                merged_delims[-1]["parent_num"] = d["parent_num"]
                merged_delims[-1]["part_label"] = d["part_label"]
                merged_delims[-1]["anchor_type"] = "explicit"
            continue
        merged_delims.append(d)

    # Assign sequential sub-labels (a, b, c) and parent numbers if in table layout
    sub_char_idx = 0
    chars = ["a", "b", "c", "d", "e"]
    for i, d in enumerate(merged_delims):
        if d.get("part_label") is None:
            # If in DAA table style with 5 marks vs 7 marks:
            # Question 1: 3 subquestions (5, 5, 5)
            # Question 2: 2 subquestions (7, 8)
            # Question 3: 2 subquestions (5, 5)
            d["parent_num"] = curr_parent
            d["part_label"] = chars[sub_char_idx % len(chars)]
            sub_char_idx += 1

    results = []

    # 3. Inter-page Continuation Resolution:
    # Content/diagrams appearing at the top of continuation page before the first delimiter
    first_delim_y = merged_delims[0]["y_min"] if merged_delims else h_img

    if open_question_from_prev_page and first_delim_y > (0.20 * h_img):
        # Extract continuation text and figure above first_delim_y
        cont_items = [it for it in content_items if max(pt[1] for pt in it[0]) < first_delim_y]
        cont_text = " ".join(str(it[1]).strip() for it in cont_items)
        cont_figs = detect_isolated_figures(page_img_bgr, content_items, 0, int(first_delim_y))

        # Crop continuation snippet
        y1_cont = 0
        y2_cont = int(first_delim_y)
        cont_crop_path = None
        if (y2_cont - y1_cont) >= 40:
            cont_filename = f"snippet_cont_p{paper_id}_pg{page_no}_{uuid.uuid4().hex[:6]}.png"
            dest_cont = os.path.join(DIAGRAM_ASSETS_DIR, cont_filename)
            cv2.imwrite(dest_cont, page_img_bgr[y1_cont:y2_cont, :])
            cont_crop_path = dest_cont

        merged_q = dict(open_question_from_prev_page)
        if cont_text:
            merged_q["question_text"] = f"{merged_q['question_text']} {cont_text}".strip()
        if cont_figs:
            merged_q["figure_path"] = cont_figs[0]["path"]
            merged_q["figure_phash"] = cont_figs[0]["phash"]
        merged_q["is_continuation"] = 1
        results.append(merged_q)
        open_question_from_prev_page = None

    if not merged_delims:
        if content_items and len(content_items) >= 2:
            # Fallback extraction: extract visible text on page as readable question so nothing is lost
            full_content_text = " ".join(str(it[1]).strip() for it in content_items)
            marks, co_tag, marks_found = parse_marks_and_co(full_content_text)
            
            y_min_all = int(min(pt[1] for it in content_items for pt in it[0]))
            y_max_all = int(max(pt[1] for it in content_items for pt in it[0]))
            
            crop_y1 = max(0, y_min_all - 10)
            crop_y2 = min(h_img, y_max_all + 10)
            crop_path = None
            if (crop_y2 - crop_y1) >= 40:
                crop_filename = f"snippet_p{paper_id}_pg{page_no}_fallback_{uuid.uuid4().hex[:6]}.png"
                dest_crop = os.path.join(DIAGRAM_ASSETS_DIR, crop_filename)
                cv2.imwrite(dest_crop, page_img_bgr[crop_y1:crop_y2, :])
                crop_path = dest_crop

            figs = detect_isolated_figures(page_img_bgr, content_items, y_min_all, y_max_all)
            
            conf_score = calculate_confidence_score(
                text=full_content_text,
                marks_found=marks_found,
                is_ocr=True,
                has_snippet=(crop_path is not None),
            )
            conf_score = min(conf_score, 0.65)

            results.append({
                "question_number": f"{curr_parent}",
                "parent_question_number": curr_parent,
                "part_label": "a",
                "question_text": full_content_text,
                "marks": marks,
                "co_tag": co_tag,
                "unit": 1,
                "topic": "General",
                "confidence_score": conf_score,
                "image_path": crop_path,
                "figure_path": figs[0]["path"] if figs else None,
                "figure_phash": figs[0]["phash"] if figs else None,
                "tag_names": suggest_tags_from_text(full_content_text),
                "page_no": page_no,
                "is_continuation": 0,
            })
            curr_parent += 1

        return results, open_question_from_prev_page, curr_parent

    # 4. Extract Questions for each delimited row
    for k in range(len(merged_delims)):
        curr_d = merged_delims[k]
        next_d = merged_delims[k + 1] if k + 1 < len(merged_delims) else None

        y_top = max(0, int(curr_d["y_min"] - 12))
        y_bot = int(next_d["y_min"] - 10) if next_d else h_img

        # Group all content items that fall within this vertical range
        row_items = [
            it for it in content_items
            if (min(pt[1] for pt in it[0]) >= (y_top - 15) and
                max(pt[1] for pt in it[0]) <= (y_bot + 15))
        ]
        if not row_items:
            row_items = [content_items[curr_d["item_idx"]]]

        row_text = " ".join(str(it[1]).strip() for it in row_items)
        marks, co_tag, marks_found = parse_marks_and_co(row_text)

        # Detect isolated figures within this question row
        figs = detect_isolated_figures(page_img_bgr, row_items, y_top, y_bot)
        fig_path = figs[0]["path"] if figs else None
        fig_phash = figs[0]["phash"] if figs else None

        # Clean display text (strip leading anchor prefixes)
        display_text = row_text
        display_text = re.sub(
            r"^(?:Q(?:uestion)?\s*[\.\:\-\)]?\s*\d{1,2}\s*[\.\:\-\)]?\s*[a-dA-D]?[\.\)\:]?|\b\d{1,2}\s*[a-dA-D]?[\.\)\:]?|[a-dA-D][\.\)\:])\s*",
            "",
            display_text,
        ).strip()
        # Also clean trailing marks/CO from text
        display_text = re.sub(r"(?:\[|\()(?:CO|C0)\s*\d{1,2}(?:\]|\)).*$", "", display_text, flags=re.I).strip()
        display_text = re.sub(r"(?:\[|\()\s*\d{1,2}\s*(?:M|Marks|marks)?\s*(?:\]|\))\s*$", "", display_text, flags=re.I).strip()

        # Crop visual snippet of question row
        crop_y1 = max(0, y_top - 5)
        crop_y2 = min(h_img, y_bot + 8)
        crop_path = None
        if (crop_y2 - crop_y1) >= 30:
            crop_filename = f"snippet_p{paper_id}_pg{page_no}_q{curr_d['parent_num']}{curr_d['part_label']}_{uuid.uuid4().hex[:6]}.png"
            dest_crop = os.path.join(DIAGRAM_ASSETS_DIR, crop_filename)
            cv2.imwrite(dest_crop, page_img_bgr[crop_y1:crop_y2, :])
            crop_path = dest_crop

        conf_score = calculate_confidence_score(
            text=row_text,
            marks_found=marks_found,
            is_ocr=True,
            has_snippet=(crop_path is not None),
        )

        inferred_tags = suggest_tags_from_text(row_text)

        q_num_str = f"{curr_d['parent_num']}{curr_d['part_label']}" if SPLIT_SUBQUESTIONS else f"{curr_d['parent_num']}"

        q_dict = {
            "question_number": q_num_str,
            "parent_question_number": curr_d["parent_num"],
            "part_label": curr_d["part_label"],
            "question_text": display_text or row_text,
            "marks": marks,
            "co_tag": co_tag,
            "unit": 1,
            "topic": "General",
            "confidence_score": conf_score,
            "image_path": crop_path,
            "figure_path": fig_path,
            "figure_phash": fig_phash,
            "tag_names": inferred_tags,
            "page_no": page_no,
            "is_continuation": 0,
        }

        # Check if the last question row extends near the bottom and continues onto next page
        if k == len(merged_delims) - 1 and y_bot > (0.82 * h_img):
            open_question_from_prev_page = q_dict
        else:
            results.append(q_dict)

    return results, open_question_from_prev_page, curr_parent
