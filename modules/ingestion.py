import hashlib
import os
import urllib.parse
from typing import Any, Callable, Dict, List, Optional, Tuple
import cv2
import numpy as np
import pymupdf

from modules.database import (
    get_db_connection,
    add_paper,
    add_question,
    add_mcq,
    get_paper_by_hash,
    get_all_subjects,
    add_subject,
    add_source_file,
    log_action,
)
from modules.hashing import compute_image_phash, find_or_create_diagram_group
from modules.metadata import match_subject
from modules.parser import (
    parse_page_questions,
)
from modules.preprocess import preprocess_page_image
from modules.segmenter import segment_pdf

_RAPID_OCR_ENGINE = None

MAX_PDF_PAGES = 150
MAX_PDF_BYTES = 100 * 1024 * 1024  # 100 MB


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


class DownloadResult(tuple):
    """Tuple subclass (success, message) that evaluates truthy if success is True."""
    def __bool__(self) -> bool:
        return bool(self[0])


def download_drive_file(drive_url: str, output_path: str) -> Tuple[bool, str]:
    """Downloads a public Google Drive file using gdown with strict validation.
    
    Verifies URL host is drive.google.com or docs.google.com.
    Verifies downloaded file <= 100 MB and starts with %PDF header.
    Returns (success: bool, message: str) wrapped in DownloadResult.
    """
    if not drive_url:
        return DownloadResult((False, "Empty Google Drive URL."))
    try:
        parsed = urllib.parse.urlparse(drive_url)
        netloc = (parsed.netloc or "").lower().split(":")[0]
        if netloc not in ("drive.google.com", "docs.google.com"):
            return DownloadResult((False, f"Invalid host '{netloc}'. URL must be from drive.google.com or docs.google.com."))
    except Exception as e:
        return DownloadResult((False, f"Malformed URL: {e}"))

    try:
        import gdown
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        gdown.download(url=drive_url, output=output_path, quiet=False, fuzzy=True)
        
        if not os.path.exists(output_path):
            return DownloadResult((False, "File could not be downloaded from Google Drive."))
            
        size = os.path.getsize(output_path)
        if size > MAX_PDF_BYTES:
            if os.path.exists(output_path):
                os.remove(output_path)
            return DownloadResult((False, f"Downloaded file exceeds 100 MB limit ({round(size / (1024 * 1024), 1)} MB)."))
            
        with open(output_path, "rb") as f:
            header = f.read(5)
        if not header.startswith(b"%PDF"):
            if os.path.exists(output_path):
                os.remove(output_path)
            return DownloadResult((False, "Downloaded file does not start with valid %PDF header."))
            
        return DownloadResult((True, "File downloaded successfully."))
    except Exception as e:
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass
        return DownloadResult((False, f"Download failed: {e}"))


def validate_pdf_bytes(file_bytes: bytes) -> Tuple[bool, str]:
    """Validates that bytes represent a valid PDF within constraints (<= 150 pages, <= 100MB)."""
    if not file_bytes:
        return False, "File is empty."
    if len(file_bytes) > MAX_PDF_BYTES:
        return False, f"File size exceeds 100 MB limit ({round(len(file_bytes) / (1024 * 1024), 1)} MB)."
    if not file_bytes.startswith(b"%PDF-"):
        return False, "Uploaded file is not a valid PDF document (missing %PDF- header)."
    
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        p_count = len(doc)
        doc.close()
        if p_count == 0:
            return False, "PDF contains 0 pages."
        if p_count > MAX_PDF_PAGES:
            return False, f"PDF exceeds maximum page limit of 150 pages (has {p_count} pages)."
    except Exception as e:
        return False, f"Corrupted or invalid PDF: {e}"

    return True, "Valid PDF"


def _report_progress(callback: Optional[Callable], msg: str, pct: float) -> None:
    """Invokes progress callback supporting both (msg, float) and (curr, total, msg) signatures."""
    if not callback:
        return
    try:
        callback(msg, pct)
    except TypeError:
        try:
            callback(int(pct * 100), 100, msg)
        except Exception:
            pass
    except Exception:
        pass


def ingest_combined_pdf(
    file_bytes: bytes,
    original_filename: str,
    actor_email: str = "diyanshah2301@gmail.com",
    progress_callback: Optional[Callable] = None,
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """Auto-detects and segregates multiple examination papers from a combined PDF document.
    
    1. Stores source file once in data/sources/.
    2. Runs modules/segmenter.py to slice per-paper PDFs into data/papers/.
    3. Matches subject via course code or RapidFuzz name similarity.
    4. Auto-accepts papers with high confidence (>= 0.85).
    5. Parses questions and crops high-resolution snippets and diagrams.
    """
    is_valid, msg = validate_pdf_bytes(file_bytes)
    if not is_valid:
        return False, msg, []

    source_sha256 = compute_file_sha256(file_bytes)

    # 1. Store source file in data/sources/
    _report_progress(progress_callback, "Saving source file...", 0.10)
    sources_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sources")
    os.makedirs(sources_dir, exist_ok=True)
    source_filename = f"source_{source_sha256[:12]}_{original_filename}"
    source_path = os.path.join(sources_dir, source_filename)

    with open(source_path, "wb") as f:
        f.write(file_bytes)

    doc_test = pymupdf.open(source_path)
    page_count = len(doc_test)
    doc_test.close()

    source_file_id = add_source_file(
        sha256=source_sha256,
        filename=original_filename,
        path=source_path,
        page_count=page_count,
    )

    # 2. Run segmenter to identify paper boundaries
    ocr_eng = get_rapid_ocr()
    detected = segment_pdf(
        source_pdf_path=source_path,
        source_sha256=source_sha256,
        source_file_id=source_file_id,
        ocr_engine=ocr_eng if ocr_eng is not False else None,
        progress_callback=progress_callback,
    )

    if not detected:
        return False, "No valid examination papers could be detected in this document.", []

    db_subjects = get_all_subjects()
    ingested_papers_summary = []

    # 3. Ingest each detected paper
    for p_info in detected:
        meta = p_info["metadata"]
        p_file_hash = p_info["file_hash"]
        p_file_path = p_info["file_path"]

        # Deduplication check
        existing = get_paper_by_hash(p_file_hash)
        if existing:
            ingested_papers_summary.append({
                "paper_id": existing["id"],
                "subject_name": "Already Ingested",
                "page_range": f"{p_info['page_start']}-{p_info['page_end']}",
                "status": "duplicate",
                "quality_score": p_info["quality_score"],
                "metadata_confidence": meta.get("metadata_confidence", 0.0),
                "questions_count": 0,
                "thumbnail_path": p_info["thumbnail_path"],
                "meta": meta,
            })
            continue

        # Match or propose subject
        c_code = meta["course_code"]["value"]
        c_name = meta["course_name"]["value"]
        sub_match = match_subject(c_code, c_name, db_subjects)

        if sub_match["matched"]:
            subj_id = sub_match["subject_id"]
            subj_name = sub_match["subject_name"]
        else:
            # Create pending / new subject
            subj_name = sub_match.get("proposed_name") or f"Course {c_code}"
            subj_id = add_subject(name=subj_name, code=c_code)
            db_subjects = get_all_subjects()  # Refresh cache

        yr = meta["year"]["value"]
        sem = meta["semester"]["value"]
        e_type = meta["exam_type"]["value"]
        is_makeup_val = meta["is_makeup"]["value"]
        max_marks_val = meta["max_marks"]["value"]
        meta_conf = meta["metadata_confidence"]

        # Auto-accept criteria: confidence >= 0.85
        initial_status = "accepted" if meta_conf >= 0.85 else "pending_review"

        paper_id = add_paper(
            subject_id=subj_id,
            year=yr,
            semester=sem,
            exam_type=e_type,
            file_hash=p_file_hash,
            file_path=p_file_path,
            source_file_id=source_file_id,
            page_start=p_info["page_start"],
            page_end=p_info["page_end"],
            course_code=c_code,
            course_name_raw=c_name,
            exam_name_raw=meta["exam_name"]["value"],
            exam_date=meta["exam_date"]["value"],
            program=meta["program"]["value"],
            branch=meta["branch"]["value"],
            study_year=meta["study_year"]["value"],
            duration_minutes=meta["duration_minutes"]["value"],
            max_marks=max_marks_val,
            is_makeup=is_makeup_val,
            quality_score=p_info["quality_score"],
            metadata_confidence=meta_conf,
            status=initial_status,
        )

        # 4. Parse Questions for this sliced paper
        paper_doc = pymupdf.open(p_file_path)
        paper_questions = []
        open_q = None
        carry_num = 1

        for p_idx in range(len(paper_doc)):
            page_obj = paper_doc[p_idx]
            pix = page_obj.get_pixmap(dpi=150)
            img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
            bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR) if pix.n == 3 else img_np
            pre = preprocess_page_image(bgr)

            ocr_res = []
            if ocr_eng:
                res, _ = ocr_eng(pre["clean_bgr"])
                if res:
                    ocr_res = res

            qs, open_q, carry_num = parse_page_questions(
                page_img_bgr=pre["clean_bgr"],
                ocr_lines=ocr_res,
                paper_id=paper_id,
                page_no=p_idx + 1,
                carry_parent_num=carry_num,
                open_question_from_prev_page=open_q,
            )
            paper_questions.extend(qs)

        if open_q:
            paper_questions.append(open_q)
        paper_doc.close()

        # 5. Commit questions to DB
        q_count = 0
        for q in paper_questions:
            q_num = q["question_number"]
            q_text = q["question_text"]
            img_path = q.get("image_path")
            fig_path = q.get("figure_path")
            fig_phash = q.get("figure_phash")

            # Diagram group matching
            diagram_grp_id = None
            if fig_phash:
                grp_id, _, _ = find_or_create_diagram_group(fig_phash, max_hamming_distance=5)
                diagram_grp_id = grp_id
            elif img_path:
                ph = compute_image_phash(img_path)
                if ph:
                    grp_id, _, _ = find_or_create_diagram_group(ph, max_hamming_distance=5)
                    diagram_grp_id = grp_id

            # Estimate syllabus unit from parent question number
            p_num = q.get("parent_question_number") or 1
            estimated_unit = max(1, min(5, (p_num + 1) // 2))

            q_id = add_question(
                paper_id=paper_id,
                question_number=q_num,
                question_text=q_text,
                content_type="diagram" if (fig_path or img_path) else "text",
                image_path=img_path,
                phash=fig_phash,
                diagram_group_id=diagram_grp_id,
                marks=q["marks"],
                unit=estimated_unit,
                topic=f"Unit {estimated_unit} Concepts",
                confidence_score=q["confidence_score"],
                is_reviewed=False,
                tag_names=q.get("tag_names", []),
                parent_question_number=p_num,
                part_label=q.get("part_label"),
                co_tag=q.get("co_tag"),
                page_no=q.get("page_no"),
                is_continuation=q.get("is_continuation", 0),
                figure_path=fig_path,
                figure_phash=fig_phash,
            )
            q_count += 1

            # Seed initial draft MCQ
            add_mcq(
                question_id=q_id,
                option_a=f"Primary analytical solution for Question {q_num}",
                option_b="Secondary alternate implementation rule",
                option_c="Neither: Represents an edge-case condition",
                option_d="Both primary concept and alternate rule apply",
                correct_option="A",
                explanation=f"Official reference answer for Question {q_num} covering Unit {estimated_unit}.",
                status="draft",
            )

        log_action(
            actor=actor_email,
            action="INGEST_PAPER_AUTOSEG",
            details=f"Ingested Paper ID {paper_id} ({subj_name}, {yr} {e_type}) with {q_count} questions.",
        )

        ingested_papers_summary.append({
            "paper_id": paper_id,
            "subject_name": subj_name,
            "page_range": f"{p_info['page_start']}-{p_info['page_end']}",
            "status": initial_status,
            "quality_score": p_info["quality_score"],
            "metadata_confidence": meta_conf,
            "questions_count": q_count,
            "thumbnail_path": p_info["thumbnail_path"],
            "meta": meta,
        })

    return True, f"Successfully processed {len(detected)} detected examination paper(s).", ingested_papers_summary


def process_pdf_document(
    file_bytes: bytes,
    original_filename: str,
    subject_id: int,
    year: int,
    semester: int,
    exam_type: str,
    actor_email: str = "diyanshah2301@gmail.com",
    *,
    progress_callback: Optional[Callable] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Manual Single Paper Ingestion Override:
    Takes explicit metadata from the user, crops snippets, and stores database records.
    """
    _report_progress(progress_callback, "Saving source PDF file...", 0.10)
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

    doc = pymupdf.open(saved_path)
    total_pages = len(doc)
    ocr_engine = get_rapid_ocr()

    all_page_questions: List[Dict[str, Any]] = []
    open_q = None
    carry_num = 1

    for page_idx in range(total_pages):
        page = doc[page_idx]
        pix = page.get_pixmap(dpi=150)
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR) if pix.n == 3 else img_np
        pre = preprocess_page_image(bgr)

        ocr_result = []
        if ocr_engine:
            res, _ = ocr_engine(pre["clean_bgr"])
            if res:
                ocr_result = res

        qs, open_q, carry_num = parse_page_questions(
            page_img_bgr=pre["clean_bgr"],
            ocr_lines=ocr_result,
            paper_id=paper_id,
            page_no=page_idx + 1,
            carry_parent_num=carry_num,
            open_question_from_prev_page=open_q,
        )
        all_page_questions.extend(qs)

    if open_q:
        all_page_questions.append(open_q)
    doc.close()

    if not all_page_questions:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM papers WHERE id = ?;", (paper_id,))
            conn.commit()
        if os.path.exists(saved_path):
            os.remove(saved_path)
        return False, "Failed to parse questions: No legible questions or anchors could be extracted.", {}

    parsed_count = 0
    extracted_snippets_count = 0
    low_confidence_count = 0

    for idx, q_data in enumerate(all_page_questions):
        q_num = q_data["question_number"]
        q_text = q_data["question_text"]
        image_path = q_data.get("image_path")
        fig_path = q_data.get("figure_path")
        fig_phash = q_data.get("figure_phash")

        if image_path or fig_path:
            extracted_snippets_count += 1

        diagram_grp_id = None
        if fig_phash:
            grp_id, _, _ = find_or_create_diagram_group(fig_phash, max_hamming_distance=5)
            diagram_grp_id = grp_id

        p_num = q_data.get("parent_question_number") or 1
        estimated_unit = max(1, min(5, (p_num + 1) // 2))

        conf = q_data.get("confidence_score", 0.9)
        if conf < 0.80:
            low_confidence_count += 1

        q_id = add_question(
            paper_id=paper_id,
            question_number=q_num,
            question_text=q_text,
            content_type="diagram" if (fig_path or image_path) else "text",
            image_path=image_path,
            phash=fig_phash,
            diagram_group_id=diagram_grp_id,
            marks=q_data.get("marks", 5.0),
            unit=estimated_unit,
            topic=f"Unit {estimated_unit} Concepts",
            confidence_score=conf,
            is_reviewed=False,
            tag_names=q_data.get("tag_names", []),
            parent_question_number=p_num,
            part_label=q_data.get("part_label"),
            co_tag=q_data.get("co_tag"),
            page_no=q_data.get("page_no"),
            is_continuation=q_data.get("is_continuation", 0),
            figure_path=fig_path,
            figure_phash=fig_phash,
        )
        parsed_count += 1

        add_mcq(
            question_id=q_id,
            option_a=f"Primary analytical solution for Question {q_num}",
            option_b="Secondary alternate implementation rule",
            option_c="Neither: Represents an edge-case condition",
            option_d="Both primary concept and alternate rule apply",
            correct_option="A",
            explanation=f"Official reference answer for Question {q_num}.",
            status="draft",
        )

    log_action(
        actor=actor_email,
        action="INGEST_PAPER_MANUAL",
        details=f"Paper ID {paper_id} ingested manually. {parsed_count} questions extracted.",
    )

    summary = {
        "paper_id": paper_id,
        "total_pages": total_pages,
        "questions_parsed": parsed_count,
        "visual_snippets_cropped": extracted_snippets_count,
        "low_confidence_review_queue": low_confidence_count,
    }

    return True, f"Successfully parsed {original_filename} into {parsed_count} questions.", summary
