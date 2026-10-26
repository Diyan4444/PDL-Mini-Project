import os
import tempfile
import cv2
import numpy as np
import pymupdf

from modules.database import get_db_connection, init_db
from modules.parser import parse_marks_and_co, parse_page_questions
from modules.preprocess import compute_quality_score, preprocess_page_image
from modules.segmenter import segment_pdf

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
DAA_PDF = os.path.join(FIXTURES_DIR, "paper_sub3_2025_midterm_9707d76d.pdf")
MATH_PDF = os.path.join(FIXTURES_DIR, "paper_sub3_2025_midterm_0105e9c3.pdf")


def test_marks_and_co_parsing():
    """Validates robust parsing of tricky marks and CO tags including OCR confusions."""
    cases = [
        ("[CO2|[7]", 7.0, "CO2"),
        ("(CO2] [8]", 8.0, "CO2"),
        ("[C02] [5]", 5.0, "CO2"),
        ("(5) CO5", 5.0, "CO5"),
        ("[s]", 5.0, None),
        ("[6]", 6.0, None),
        ("(10)", 10.0, None),
        ("(3).C07", 3.0, "CO7"),
        ("(2) CO7", 2.0, "CO7"),
        ("(4) :C06", 4.0, "CO6"),
    ]

    for raw_str, exp_marks, exp_co in cases:
        marks, co, found = parse_marks_and_co(raw_str)
        assert marks == exp_marks, f"Failed marks for {raw_str}: expected {exp_marks}, got {marks}"
        if exp_co is not None:
            assert co == exp_co, f"Failed CO for {raw_str}: expected {exp_co}, got {co}"


def test_database_migrations_idempotency():
    """Validates that database initialization and migrations are strictly idempotent."""
    init_db()
    init_db()  # Second call must not fail

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Verify papers table columns
        cursor.execute("PRAGMA table_info(papers);")
        p_cols = {row["name"] for row in cursor.fetchall()}
        expected_paper_cols = {
            "source_file_id", "page_start", "page_end", "course_code", "course_name_raw",
            "exam_name_raw", "exam_date", "program", "branch", "study_year",
            "duration_minutes", "max_marks", "is_makeup", "quality_score", "metadata_confidence", "status"
        }
        assert expected_paper_cols.issubset(p_cols), f"Missing columns in papers: {expected_paper_cols - p_cols}"

        # Verify questions table columns
        cursor.execute("PRAGMA table_info(questions);")
        q_cols = {row["name"] for row in cursor.fetchall()}
        expected_q_cols = {
            "parent_question_number", "part_label", "co_tag", "page_no", "bbox_json",
            "is_continuation", "figure_path", "figure_phash"
        }
        assert expected_q_cols.issubset(q_cols), f"Missing columns in questions: {expected_q_cols - q_cols}"

        # Verify mcq_bank status column
        cursor.execute("PRAGMA table_info(mcq_bank);")
        mcq_cols = {row["name"] for row in cursor.fetchall()}
        assert "status" in mcq_cols

        # Verify source_files table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='source_files';")
        assert cursor.fetchone() is not None


def test_degraded_image_quality_score():
    """Validates that degraded images report a lower quality score and survive preprocessing."""
    doc = pymupdf.open(DAA_PDF)
    pix = doc[0].get_pixmap(dpi=150)
    doc.close()

    img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
    clean_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR) if pix.n == 3 else img_np

    clean_score = compute_quality_score(cv2.cvtColor(clean_bgr, cv2.COLOR_BGR2GRAY))

    # Apply synthetic degradation: blur + shadow gradient + 3-degree rotation
    h, w = clean_bgr.shape[:2]
    blurred = cv2.GaussianBlur(clean_bgr, (9, 9), sigmaX=2.0)
    
    # Shadow gradient
    grad = np.tile(np.linspace(0.4, 1.0, w), (h, 1))
    shadowed = (blurred * grad[:, :, np.newaxis]).astype(np.uint8)

    # 3-degree rotation
    M = cv2.getRotationMatrix2D((w // 2, h // 2), 3.0, 1.0)
    degraded = cv2.warpAffine(shadowed, M, (w, h), borderValue=(255, 255, 255))

    degraded_score = compute_quality_score(cv2.cvtColor(degraded, cv2.COLOR_BGR2GRAY))
    assert degraded_score < clean_score, "Degraded image should have lower quality score"

    # Preprocessing should recover and deskew without crashing
    pre = preprocess_page_image(degraded)
    assert pre["clean_bgr"] is not None
    assert pre["binarized"] is not None


def test_daa_fixture_pipeline():
    """Tests DAA fixture:
    - 1 paper detected
    - Exactly 7 sub-questions extracted
    - Total marks sum = 40.0
    - Dijkstra continuation resolved (is_continuation=1)
    - 4 figure crops saved to disk
    """
    assert os.path.exists(DAA_PDF), f"Fixture not found: {DAA_PDF}"
    
    doc = pymupdf.open(DAA_PDF)
    assert len(doc) == 2, "DAA PDF should have 2 pages"

    all_qs = []
    open_q = None
    carry_num = 1
    figure_paths = set()

    for p_idx in range(len(doc)):
        pix = doc[p_idx].get_pixmap(dpi=150)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR) if pix.n == 3 else img
        pre = preprocess_page_image(bgr)

        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()
        res, _ = ocr(pre["clean_bgr"])

        qs, open_q, carry_num = parse_page_questions(
            page_img_bgr=pre["clean_bgr"],
            ocr_lines=res,
            paper_id=101,
            page_no=p_idx + 1,
            carry_parent_num=carry_num,
            open_question_from_prev_page=open_q,
        )
        all_qs.extend(qs)

    if open_q:
        all_qs.append(open_q)
    doc.close()

    assert len(all_qs) == 7, f"Expected 7 subquestions, got {len(all_qs)}"
    total_marks = sum(q["marks"] for q in all_qs)
    assert total_marks == 40.0, f"Expected 40.0 total marks, got {total_marks}"

    # Check continuation
    has_continuation = any(q.get("is_continuation") == 1 for q in all_qs)
    assert has_continuation, "Dijkstra continuation across pages was not marked as is_continuation=1"

    # Check figures
    for q in all_qs:
        if q.get("figure_path") and os.path.exists(q["figure_path"]):
            figure_paths.add(q["figure_path"])

    assert len(figure_paths) >= 4, f"Expected at least 4 figure crops, found {len(figure_paths)}"


def test_math_fixture_pipeline():
    """Tests Math fixture:
    - 4 pages containing 2 papers
    - Paper 1: regular midterm (is_makeup=0)
    - Paper 2: make-up midterm (is_makeup=1)
    - Course code: R5MA2007T
    """
    assert os.path.exists(MATH_PDF), f"Fixture not found: {MATH_PDF}"

    detected = segment_pdf(MATH_PDF, source_sha256="test_math_fixture_sha")
    assert len(detected) == 2, f"Expected 2 papers in Math fixture, got {len(detected)}"

    p1 = detected[0]
    p2 = detected[1]

    assert p1["page_start"] == 1 and p1["page_end"] == 2
    assert p2["page_start"] == 3 and p2["page_end"] == 4

    meta1 = p1["metadata"]
    meta2 = p2["metadata"]

    assert meta1["is_makeup"]["value"] == 0, "Paper 1 should be regular exam"
    assert meta2["is_makeup"]["value"] == 1, "Paper 2 should be make-up exam"

    assert meta1["course_code"]["value"] == "R5MA2007T"
    assert meta2["course_code"]["value"] == "R5MA2007T"
    assert meta1["exam_type"]["value"] == "midterm"
    assert meta2["exam_type"]["value"] == "midterm"


def test_concatenated_fixtures():
    """Tests concatenated PDF (6 pages: Math 4 pages + DAA 2 pages):
    - Detects 3 discrete examination papers in order.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_concat_path = tmp.name

    doc_concat = pymupdf.open()
    doc_math = pymupdf.open(MATH_PDF)
    doc_daa = pymupdf.open(DAA_PDF)

    doc_concat.insert_pdf(doc_math)
    doc_concat.insert_pdf(doc_daa)
    doc_concat.save(tmp_concat_path)
    doc_concat.close()
    doc_math.close()
    doc_daa.close()

    try:
        detected = segment_pdf(tmp_concat_path, source_sha256="test_concat_sha")
        assert len(detected) == 3, f"Expected 3 papers in concatenated 6-page PDF, got {len(detected)}"

        # Paper 1: Math Regular
        assert detected[0]["page_start"] == 1 and detected[0]["page_end"] == 2
        assert detected[0]["metadata"]["course_code"]["value"] == "R5MA2007T"
        assert detected[0]["metadata"]["is_makeup"]["value"] == 0

        # Paper 2: Math Makeup
        assert detected[1]["page_start"] == 3 and detected[1]["page_end"] == 4
        assert detected[1]["metadata"]["course_code"]["value"] == "R5MA2007T"
        assert detected[1]["metadata"]["is_makeup"]["value"] == 1

        # Paper 3: DAA Regular
        assert detected[2]["page_start"] == 5 and detected[2]["page_end"] == 6
        assert detected[2]["metadata"]["course_code"]["value"] == "R5IT2002T"
        assert detected[2]["metadata"]["is_makeup"]["value"] == 0

    finally:
        try:
            if os.path.exists(tmp_concat_path):
                os.remove(tmp_concat_path)
        except Exception:
            pass
