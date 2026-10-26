import hashlib
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple
import cv2
import numpy as np
import pymupdf

from modules.metadata import extract_metadata
from modules.preprocess import preprocess_page_image

HEADER_KEYWORDS = [
    r"EXAMINATION",
    r"DATE\s*OF\s*EXAM",
    r"SEMESTER\s*[\&\+]\s*PROGRAM",
    r"COURSE\s*NAME",
    r"TIME\s*ALLOWED",
    r"MAX\.?\s*MARKS",
    r"AUTONOMOUS\s*INSTITUTE",
    r"VEERMATA\s*JIJABAI",
    r"VJTI",
    r"INSTRUCTIONS",
]

END_MARKERS = [
    r"\bEND\s+OF\s+PAPER\b",
    r"\bALL\s+THE\s+BEST\b",
    r"\bBEST\s+OF\s+LUCK\b",
    r"\*{5,}",
    r"\-{5,}",
]


def classify_page_header(text_lines: List[str], word_count: int, quality_score: float) -> str:
    """Classifies a page into 'FIRST_PAGE', 'CONTINUATION', 'BLANK', or 'OTHER'.
    
    Uses header table keyword density, layout signals, and ink ratio.
    """
    if word_count < 5 and quality_score < 0.2:
        return "BLANK"

    # Search top 20 lines for institutional header signatures
    top_text = " ".join(text_lines[:20]).upper()
    
    matches = 0
    for kw in HEADER_KEYWORDS:
        if re.search(kw, top_text):
            matches += 1

    # First page threshold: at least 3 distinct exam header keywords
    if matches >= 3:
        return "FIRST_PAGE"

    return "CONTINUATION"


def has_end_marker(text_lines: List[str]) -> bool:
    """Checks if the page contains a formal end-of-paper marker in its bottom section."""
    bottom_text = " ".join(text_lines[-15:]).upper()
    for marker in END_MARKERS:
        if re.search(marker, bottom_text):
            return True
    return False


def slice_pdf_pages(
    source_pdf_path: str,
    page_start: int,
    page_end: int,
    output_path: str,
) -> bool:
    """Extracts a page range [page_start, page_end] (1-indexed, inclusive) into a standalone PDF."""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        src_doc = pymupdf.open(source_pdf_path)
        dst_doc = pymupdf.open()
        # insert_pdf expects 0-indexed [from_page, to_page] inclusive
        dst_doc.insert_pdf(src_doc, from_page=page_start - 1, to_page=page_end - 1)
        dst_doc.save(output_path)
        dst_doc.close()
        src_doc.close()
        return True
    except Exception as e:
        print(f"Error slicing PDF from {page_start} to {page_end}: {e}")
        return False


def segment_pdf(
    source_pdf_path: str,
    source_sha256: str,
    source_file_id: Optional[int] = None,
    output_dir: Optional[str] = None,
    ocr_engine: Optional[Any] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> List[Dict[str, Any]]:
    """Analyzes a multi-paper or combined PDF, segregating it into discrete examination papers.
    
    For each paper detected:
    - Slices pages into data/papers/
    - Computes deterministic file hash: sha256(source_sha256 + ":" + start + "-" + end)
    - Extracts metadata and computes quality score
    - Generates first-page preview thumbnail
    """
    if not output_dir:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "papers")
    os.makedirs(output_dir, exist_ok=True)

    doc = pymupdf.open(source_pdf_path)
    total_pages = len(doc)
    
    if total_pages == 0:
        doc.close()
        return []

    # Initialize OCR lazily if needed
    if ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            ocr_engine = RapidOCR()
        except Exception:
            ocr_engine = None

    # Step 1: Analyze each page
    page_records = []
    for p_idx in range(total_pages):
        page = doc[p_idx]
        page_num = p_idx + 1
        if progress_callback:
            progress_callback(page_num, total_pages, f"Analyzing page {page_num} of {total_pages}...")

        # 1. Try native text layer
        native_text = page.get_text("text").strip()
        native_words = page.get_text("words")
        word_count = len(native_words)

        # 2. Render pixmap for image analysis & OCR fallback
        pix = page.get_pixmap(dpi=150)
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR) if pix.n == 3 else img_np
        
        # Preprocessing & quality score
        pre_res = preprocess_page_image(bgr)
        clean_bgr = pre_res["clean_bgr"]
        quality_score = pre_res["quality_score"]

        # If native text is too sparse, run RapidOCR
        if word_count < 25 and ocr_engine:
            ocr_res, _ = ocr_engine(clean_bgr)
            ocr_lines = [r[1] for r in ocr_res] if ocr_res else []
            full_text = "\n".join(ocr_lines)
            word_count = sum(len(l.split()) for l in ocr_lines)
        else:
            ocr_lines = [l.strip() for l in native_text.splitlines() if l.strip()]
            full_text = native_text

        # Classify page
        page_type = classify_page_header(ocr_lines, word_count, quality_score)
        is_end = has_end_marker(ocr_lines)

        page_records.append({
            "page_num": page_num,
            "page_type": page_type,
            "is_end": is_end,
            "text_lines": ocr_lines,
            "full_text": full_text,
            "quality_score": quality_score,
            "clean_bgr": clean_bgr,
        })

    # Step 2: Determine paper boundaries
    papers_spans = []
    curr_start = None
    curr_first_page_idx = None

    for i, p in enumerate(page_records):
        if p["page_type"] == "FIRST_PAGE":
            if curr_start is not None:
                # Close previous paper at previous page
                papers_spans.append({
                    "start": curr_start,
                    "end": page_records[i - 1]["page_num"],
                    "first_page_idx": curr_first_page_idx,
                })
            curr_start = p["page_num"]
            curr_first_page_idx = i
        elif p["is_end"] and curr_start is not None:
            # End marker reached
            papers_spans.append({
                "start": curr_start,
                "end": p["page_num"],
                "first_page_idx": curr_first_page_idx,
            })
            curr_start = None
            curr_first_page_idx = None

    if curr_start is not None:
        papers_spans.append({
            "start": curr_start,
            "end": page_records[-1]["page_num"],
            "first_page_idx": curr_first_page_idx,
        })

    # Fallback: if no FIRST_PAGE detected, treat whole file as 1 paper
    if not papers_spans:
        papers_spans.append({
            "start": 1,
            "end": total_pages,
            "first_page_idx": 0,
        })

    # Step 3: Slice and generate per-paper outputs
    detected_papers = []
    for idx, span in enumerate(papers_spans):
        start_p = span["start"]
        end_p = span["end"]
        first_idx = span["first_page_idx"] if span["first_page_idx"] is not None else (start_p - 1)

        # Deterministic paper file hash
        hash_seed = f"{source_sha256}:{start_p}-{end_p}"
        paper_file_hash = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()
        
        paper_filename = f"paper_seg_{source_sha256[:8]}_{start_p}_{end_p}.pdf"
        paper_filepath = os.path.join(output_dir, paper_filename)

        # Write per-paper PDF
        slice_pdf_pages(source_pdf_path, start_p, end_p, paper_filepath)

        # Extract metadata from the paper's first page
        first_rec = page_records[first_idx]
        meta = extract_metadata(first_rec["text_lines"], first_rec["full_text"])

        # Average quality score across pages in span
        span_scores = [page_records[p - 1]["quality_score"] for p in range(start_p, end_p + 1)]
        avg_quality = round(sum(span_scores) / max(1, len(span_scores)), 3)

        # Save thumbnail preview of first page
        thumb_filename = f"thumb_{paper_file_hash[:12]}.jpg"
        thumb_dir = os.path.join(os.path.dirname(output_dir), "..", "assets", "diagrams")
        os.makedirs(thumb_dir, exist_ok=True)
        thumb_path = os.path.join(thumb_dir, thumb_filename)
        cv2.imwrite(thumb_path, first_rec["clean_bgr"])

        detected_papers.append({
            "paper_index": idx + 1,
            "source_file_id": source_file_id,
            "page_start": start_p,
            "page_end": end_p,
            "file_hash": paper_file_hash,
            "file_path": paper_filepath,
            "thumbnail_path": thumb_path,
            "quality_score": avg_quality,
            "metadata": meta,
            "page_count": (end_p - start_p + 1),
            "page_records": [page_records[p - 1] for p in range(start_p, end_p + 1)],
        })

    doc.close()
    return detected_papers
