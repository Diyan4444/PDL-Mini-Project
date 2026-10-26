import hashlib
import io
import os
import re
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Tuple
import pymupdf as fitz
from PIL import Image
import pytesseract

from modules.database import (
    add_paper,
    add_question,
    add_mcq,
    get_paper_by_hash,
    log_action,
)
from modules.hashing import compute_image_phash, find_or_create_diagram_group
from modules.parser import (
    calculate_confidence_score,
    crop_page_images,
    extract_marks_from_text,
    split_text_into_questions,
    suggest_tags_from_text,
)


def compute_file_sha256(file_bytes: bytes) -> str:
    """Computes SHA-256 checksum string for deduplication."""
    return hashlib.sha256(file_bytes).hexdigest()


def download_drive_file(drive_url: str, output_path: str) -> bool:
    """Downloads a public Google Drive file using gdown."""
    try:
        import gdown
        gdown.download(url=drive_url, output=output_path, quiet=False, fuzzy=True)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 100
    except Exception:
        return False


def run_ocr_on_page(page: fitz.Page) -> str:
    """Renders page to high-DPI image and extracts text using Tesseract OCR."""
    try:
        zoom = 2.0  # 144 DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        ocr_text = pytesseract.image_to_string(img, config="--oem 3 --psm 6")
        return ocr_text
    except Exception:
        # Fallback if tesseract executable is not installed or raises an error
        return ""


def process_pdf_document(
    file_bytes: bytes,
    original_filename: str,
    subject_id: int,
    year: int,
    semester: int,
    exam_type: str,
    actor_email: str = "diyanshah2301@gmail.com",
) -> Tuple[bool, str, Dict[str, Any]]:
    """Complete ingestion pipeline: validation, text parsing, OCR fallback,
    diagram extraction, hashing, splitting, confidence evaluation, and database commits.
    
    Returns:
        (success_bool, message, summary_dict)
    """
    file_hash = compute_file_sha256(file_bytes)
    
    # 1. Deduplication check
    existing = get_paper_by_hash(file_hash)
    if existing:
        return False, f"Duplicate Paper Rejected: This document has already been ingested (Paper ID: {existing['id']}, Year: {existing['year']}).", {}

    # 2. Persist PDF to disk
    papers_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "papers")
    os.makedirs(papers_dir, exist_ok=True)
    saved_filename = f"paper_sub{subject_id}_{year}_{exam_type}_{file_hash[:8]}.pdf"
    saved_path = os.path.join(papers_dir, saved_filename)
    
    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    # 3. Insert Paper Record
    paper_id = add_paper(
        subject_id=subject_id,
        year=year,
        semester=semester,
        exam_type=exam_type,
        file_hash=file_hash,
        file_path=saved_path,
    )

    doc = fitz.open(saved_path)
    total_pages = len(doc)
    parsed_questions_count = 0
    low_confidence_count = 0
    extracted_diagrams_count = 0

    accumulated_full_text = ""
    page_crops_map: Dict[int, List[Dict[str, Any]]] = {}

    # 4. Read pages, extract visuals, and apply OCR if necessary
    for page_idx in range(total_pages):
        page = doc[page_idx]
        direct_text = page.get_text("text").strip()
        is_page_ocr = False

        # If page has very little selectable text, trigger OCR fallback
        if len(direct_text) < 150:
            ocr_text = run_ocr_on_page(page)
            if len(ocr_text) > len(direct_text):
                direct_text = ocr_text
                is_page_ocr = True

        accumulated_full_text += f"\n--- Page {page_idx + 1} ---\n" + direct_text

        # Extract embedded images and diagrams
        crops = crop_page_images(page, paper_id, page_idx)
        if crops:
            page_crops_map[page_idx] = crops
            extracted_diagrams_count += len(crops)

    doc.close()

    # 5. Split document into individual question items
    raw_questions = split_text_into_questions(accumulated_full_text)

    # 6. Process each question, classify visuals, compute pHash, evaluate confidence
    all_crops_flat = [crop for sublist in page_crops_map.values() for crop in sublist]
    crop_cursor = 0

    for idx, q_data in enumerate(raw_questions):
        q_num = q_data["question_number"]
        q_text = q_data["question_text"]
        
        marks, marks_found = extract_marks_from_text(q_text, default_marks=5.0)
        auto_tags = suggest_tags_from_text(q_text)

        content_type = "text"
        image_path = None
        phash_val = None
        diagram_grp_id = None

        # Associate visual crop if question contains diagram keywords or if visual is available
        has_diagram_kw = any(t in auto_tags for t in ["diagram", "draw", "graph", "architecture"])
        if has_diagram_kw and crop_cursor < len(all_crops_flat):
            chosen_crop = all_crops_flat[crop_cursor]
            crop_cursor += 1
            content_type = "diagram"
            image_path = chosen_crop["path"]
            phash_val = compute_image_phash(image_path)
            if phash_val:
                grp_id, _, _ = find_or_create_diagram_group(phash_val, max_hamming_distance=5)
                diagram_grp_id = grp_id
        
        # Estimate syllabus unit (approximate based on question number sequence: Q1/Q2 -> Unit 1, etc.)
        try:
            num_int = int(re.sub(r"\D", "", q_num)) if re.sub(r"\D", "", q_num) else (idx + 1)
            estimated_unit = max(1, min(5, (num_int + 1) // 2))
        except Exception:
            estimated_unit = 1

        confidence = calculate_confidence_score(
            text=q_text,
            marks_found=marks_found,
            is_ocr=False,
            has_diagram=(image_path is not None)
        )
        is_reviewed = (confidence >= 0.80)
        if not is_reviewed:
            low_confidence_count += 1

        # Commit question
        q_id = add_question(
            paper_id=paper_id,
            question_number=q_num,
            question_text=q_text,
            content_type=content_type,
            image_path=image_path,
            phash=phash_val,
            diagram_group_id=diagram_grp_id,
            marks=marks,
            unit=estimated_unit,
            topic=f"Unit {estimated_unit} Concepts",
            confidence_score=confidence,
            is_reviewed=is_reviewed,
            tag_names=auto_tags,
        )
        parsed_questions_count += 1

        # Seed initial starter MCQ entry for student quiz bank
        add_mcq(
            question_id=q_id,
            option_a=f"Standard primary concept in {q_text[:30]}...",
            option_b="Secondary alternate implementation rule",
            option_c="Neither: It represents an edge-case condition",
            option_d="Both primary concept and alternate rule apply",
            correct_option="A",
            explanation=f"Based on historical analysis of past paper question {q_num} covering Unit {estimated_unit}.",
        )

    log_action(
        actor=actor_email,
        action="INGEST_PAPER",
        details=f"Paper ID {paper_id} ingested. {parsed_questions_count} questions extracted ({low_confidence_count} need review).",
    )

    summary = {
        "paper_id": paper_id,
        "total_pages": total_pages,
        "questions_parsed": parsed_questions_count,
        "diagrams_extracted": extracted_diagrams_count,
        "low_confidence_review_queue": low_confidence_count,
    }

    return True, f"Successfully parsed and ingested {original_filename} ({parsed_questions_count} questions).", summary
