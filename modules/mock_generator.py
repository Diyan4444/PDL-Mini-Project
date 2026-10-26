from typing import Any, Dict, List
from modules.database import get_db_connection
from modules.scoring import calculate_cluster_predictions


def generate_mock_paper(
    subject_id: int,
    exam_type: str = "endterm",
    target_marks: int = 100,
) -> Dict[str, Any]:
    """Generates a structured mock examination paper using top-ranked predicted questions,
    adhering strictly to standard syllabus unit distribution and target total marks.
    
    Supports:
    - Midterm: 40 Marks (Units 1 & 2 focus)
    - Endterm: 100 Marks (Comprehensive Units 1 to 5)
    """
    predictions = calculate_cluster_predictions(subject_id, exam_type=exam_type)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, code FROM subjects WHERE id = ?;", (subject_id,))
        subj = dict(cursor.fetchone())

        # Determine department/branch from most recent paper
        cursor.execute(
            """
            SELECT branch, program 
            FROM papers 
            WHERE subject_id = ? AND (branch IS NOT NULL OR program IS NOT NULL)
            ORDER BY year DESC, id DESC LIMIT 1;
            """,
            (subject_id,),
        )
        p_meta = cursor.fetchone()
        department = "EXAMINATION"
        if p_meta:
            department = (p_meta["branch"] or p_meta["program"] or "EXAMINATION").strip().upper()

    paper_sections = []
    accumulated_marks = 0.0
    used_texts = set()
    warnings: List[str] = []

    if exam_type.lower() == "midterm" or target_marks <= 40:
        target_marks = 40
        # Midterm Blueprint: Units 1 and 2
        mid_preds = [p for p in predictions if p["unit"] in [1, 2]]
        if not mid_preds:
            mid_preds = predictions  # Fallback if units aren't tagged strictly

        # Section A: 4 questions x 5 marks = 20 marks
        sec_a_q = []
        for p in mid_preds:
            if p["question_text"] not in used_texts and len(sec_a_q) < 4:
                used_texts.add(p["question_text"])
                sec_a_q.append({
                    "q_num": f"Q{len(sec_a_q) + 1}",
                    "text": p["question_text"],
                    "marks": 5.0,
                    "unit": p["unit"],
                    "topic": p["topic"],
                    "likelihood": p["likelihood"],
                    "image_path": p["image_path"],
                })
                accumulated_marks += 5.0

        paper_sections.append({
            "section_name": "Part A (Short Analytical Questions - 20 Marks)",
            "instructions": "Answer all questions. Each question carries 5 marks.",
            "questions": sec_a_q,
        })

        # Section B: 2 questions x 10 marks = 20 marks
        sec_b_q = []
        for p in mid_preds:
            if p["question_text"] not in used_texts and len(sec_b_q) < 2:
                used_texts.add(p["question_text"])
                sec_b_q.append({
                    "q_num": f"Q{len(sec_a_q) + len(sec_b_q) + 1}",
                    "text": p["question_text"],
                    "marks": 10.0,
                    "unit": p["unit"],
                    "topic": p["topic"],
                    "likelihood": p["likelihood"],
                    "image_path": p["image_path"],
                })
                accumulated_marks += 10.0

        paper_sections.append({
            "section_name": "Part B (Long Comprehensive Questions - 20 Marks)",
            "instructions": "Answer all questions. Each question carries 10 marks.",
            "questions": sec_b_q,
        })

    else:
        target_marks = 100
        # Endterm Blueprint: Units 1 to 5
        # Part A: 10 questions x 2 marks = 20 marks
        sec_a_q = []
        for p in predictions:
            if p["question_text"] not in used_texts and len(sec_a_q) < 10:
                idx = len(sec_a_q)
                used_texts.add(p["question_text"])
                sec_a_q.append({
                    "q_num": f"1({chr(97 + idx)})",
                    "text": p["question_text"],
                    "marks": 2.0,
                    "unit": p["unit"],
                    "topic": p["topic"],
                    "likelihood": p["likelihood"],
                    "image_path": p["image_path"],
                })
                accumulated_marks += 2.0

        paper_sections.append({
            "section_name": "Part A (Mandatory Short Questions - 20 Marks)",
            "instructions": "Answer all sub-questions. Each carries 2 marks.",
            "questions": sec_a_q,
        })

        # Part B: 5 Units x 16 marks = 80 marks
        sec_b_q = []
        q_counter = 2
        for unit_idx in range(1, 6):
            unit_candidates = [
                p for p in predictions 
                if p["unit"] == unit_idx and p["question_text"] not in used_texts
            ]
            if unit_candidates:
                chosen = unit_candidates[0]
                used_texts.add(chosen["question_text"])
                sec_b_q.append({
                    "q_num": f"Q{q_counter}",
                    "text": chosen["question_text"],
                    "marks": 16.0,
                    "unit": chosen["unit"],
                    "topic": chosen["topic"],
                    "likelihood": chosen["likelihood"],
                    "image_path": chosen["image_path"],
                })
                accumulated_marks += 16.0
                q_counter += 1
            else:
                warnings.append(f"No question available for Unit {unit_idx}")

        paper_sections.append({
            "section_name": "Part B (Unit-wise Detailed Questions - 80 Marks)",
            "instructions": "Answer one full question from each unit. Each full question carries 16 marks.",
            "questions": sec_b_q,
        })

    actual_marks = int(accumulated_marks)
    if actual_marks != target_marks:
        warnings.append(f"Total paper marks ({actual_marks}) differ from target marks ({target_marks}).")

    return {
        "subject_name": subj["name"],
        "subject_code": subj["code"] or "UNIV-EXAM",
        "department": department,
        "exam_type": exam_type.upper(),
        "total_marks": actual_marks,
        "target_marks": target_marks,
        "sections": paper_sections,
        "warnings": warnings,
    }
