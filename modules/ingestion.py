import hashlib
import io
import os
import re
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Tuple
import pymupdf as fitz
from PIL import Image
import numpy as np

from modules.database import (
    get_db_connection,
    add_paper,
    add_question,
    add_mcq,
    get_paper_by_hash,
    log_action,
)
from modules.hashing import compute_image_phash, find_or_create_diagram_group
from modules.parser import (
    calculate_confidence_score,
    extract_page_question_blocks_with_crops,
    suggest_tags_from_text,
)

_RAPID_OCR_ENGINE = None


def get_rapid_ocr():
    """Initializes and returns cached RapidOCR instance."""
    global _RAPID_OCR_ENGINE
    if _RAPID_OCR_ENGINE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _RAPID_OCR_ENGINE = RapidOCR()
        except Exception:
            _RAPID_OCR_ENGINE = False
    return _RAPID_OCR_ENGINE


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


def process_pdf_document(
    file_bytes: bytes,
    original_filename: str,
    subject_id: int,
    year: int,
    semester: int,
    exam_type: str,
    actor_email: str = "diyanshah2301@gmail.com",
) -> Tuple[bool, str, Dict[str, Any]]:
    """Complete ingestion pipeline with Option 2 Visual Question Cropping:
    Extracts clubbed questions (1A+1B+1C), crops high-resolution question snippets
    preserving all math symbols, and stores database records.
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
    extracted_snippets_count = 0
    ocr_engine = get_rapid_ocr()

    all_page_questions: List[Dict[str, Any]] = []

    # 4. Process each page: render high-res image & extract clubbed question blocks with visual crops
    for page_idx in range(total_pages):
        page = doc[page_idx]
        
        # Render high-res page image (150 DPI)
        pix = page.get_pixmap(dpi=150)
        page_img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        img_np = np.array(page_img)

        # Run OCR
        ocr_result = []
        if ocr_engine:
            res, _ = ocr_engine(img_np)
            if res:
                ocr_result = res

        # Extract clubbed questions with image snippets
        page_q_blocks = extract_page_question_blocks_with_crops(
            page_img=page_img,
            ocr_lines=ocr_result,
            paper_id=paper_id,
            page_idx=page_idx,
        )

        for q in page_q_blocks:
            all_page_questions.append(q)

    doc.close()

    if not all_page_questions:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM papers WHERE id = ?;", (paper_id,))
            conn.commit()
        return False, "Failed to parse questions: No legible text or question boundaries (e.g. Q.1, Q.2) could be extracted from this document.", {}

    # 5. Commit questions with visual crops, pHash, tags & confidence scores
    for idx, q_data in enumerate(all_page_questions):
        q_num = q_data["question_number"]
        q_text = q_data["question_text"]
        image_path = q_data.get("image_path")
        marks = q_data.get("marks", 5.0)
        marks_found = q_data.get("marks_found", True)

        auto_tags = suggest_tags_from_text(q_text)
        phash_val = None
        diagram_grp_id = None

        if image_path:
            extracted_snippets_count += 1
            phash_val = compute_image_phash(image_path)
            if phash_val:
                grp_id, _, _ = find_or_create_diagram_group(phash_val, max_hamming_distance=5)
                diagram_grp_id = grp_id

        # Estimate syllabus unit
        try:
            num_int = int(re.sub(r"\D", "", q_num)) if re.sub(r"\D", "", q_num) else (idx + 1)
            estimated_unit = max(1, min(5, (num_int + 1) // 2))
        except Exception:
            estimated_unit = 1

        confidence = calculate_confidence_score(
            text=q_text,
            marks_found=marks_found,
            is_ocr=True,
            has_snippet=(image_path is not None),
        )
        is_reviewed = (confidence >= 0.80)
        if not is_reviewed:
            low_confidence_count += 1

        # Commit question
        q_id = add_question(
            paper_id=paper_id,
            question_number=q_num,
            question_text=q_text,
            content_type="diagram" if image_path else "text",
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
        preview_text = q_text[:50].replace("\n", " ")
        add_mcq(
            question_id=q_id,
            option_a=f"Primary analytical solution for Question {q_num}",
            option_b="Secondary alternate implementation rule",
            option_c="Neither: Represents an edge-case condition",
            option_d="Both primary concept and alternate rule apply",
            correct_option="A",
            explanation=f"Official solution reference for Question {q_num} covering Unit {estimated_unit}.",
        )

    log_action(
        actor=actor_email,
        action="INGEST_PAPER",
        details=f"Paper ID {paper_id} ingested. {parsed_questions_count} clubbed questions extracted with visual snippets.",
    )

    summary = {
        "paper_id": paper_id,
        "total_pages": total_pages,
        "questions_parsed": parsed_questions_count,
        "visual_snippets_cropped": extracted_snippets_count,
        "low_confidence_review_queue": low_confidence_count,
    }

    return True, f"Successfully parsed {original_filename} into {parsed_questions_count} questions with high-resolution visual question snippets.", summary
