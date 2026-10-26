import random
import time
from typing import Any, Dict, List, Optional
import streamlit as st
from modules.database import get_db_connection


def load_quiz_questions(
    subject_id: int,
    exam_type: Optional[str] = None,
    units: Optional[List[int]] = None,
    text_only: bool = False,
    limit: int = 15,
    require_verified: bool = True,
    *,
    student_id: Optional[str] = None,
    weak_topics: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Loads and formats questions for a student quiz based on selected filters and adaptivity.
    
    Filters to verified MCQs by default, excluding archived MCQs.
    Weights questions toward weak topics and down-weights recently correctly answered questions.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check count of verified MCQs first
        cursor.execute(
            """
            SELECT COUNT(*) FROM mcq_bank m
            JOIN questions q ON m.question_id = q.id
            JOIN papers p ON q.paper_id = p.id
            WHERE p.subject_id = ? AND m.status = 'verified';
            """,
            (subject_id,),
        )
        verified_count = cursor.fetchone()[0]

        # Use verified filter if available or required, otherwise exclude archived
        status_filter = "AND m.status = 'verified'" if (verified_count > 0 and require_verified) else "AND m.status != 'archived'"

        def _fetch_rows(s_filter: str) -> List[Dict[str, Any]]:
            q_str = f"""
                SELECT 
                    q.id, q.question_number, q.question_text, q.content_type, 
                    q.image_path, q.marks, q.unit, q.topic, p.year, p.exam_type,
                    m.option_a, m.option_b, m.option_c, m.option_d, m.correct_option, m.explanation
                FROM mcq_bank m
                JOIN questions q ON m.question_id = q.id
                JOIN papers p ON q.paper_id = p.id
                WHERE p.subject_id = ? {s_filter}
            """
            p_list: List[Any] = [subject_id]
            if exam_type:
                q_str += " AND p.exam_type = ?"
                p_list.append(exam_type.lower())
            if units:
                placeholders = ",".join(["?"] * len(units))
                q_str += f" AND q.unit IN ({placeholders})"
                p_list.extend(units)
            if text_only:
                q_str += " AND q.content_type = 'text'"
            q_str += " ORDER BY p.year DESC LIMIT ?;"
            p_list.append(limit * 4)
            cursor.execute(q_str, tuple(p_list))
            return [dict(r) for r in cursor.fetchall()]

        rows = _fetch_rows(status_filter)

        # Fallback 1: If verified filter yielded no rows for selected units, try non-archived pool
        if not rows and status_filter != "AND m.status != 'archived'":
            rows = _fetch_rows("AND m.status != 'archived'")

        # Fallback 2: If still no rows, check if no active MCQs exist for this subject at all and generate on-the-fly
        if not rows:
            cursor.execute(
                """
                SELECT COUNT(*) FROM mcq_bank m
                JOIN questions q ON m.question_id = q.id
                JOIN papers p ON q.paper_id = p.id
                WHERE p.subject_id = ? AND m.status != 'archived';
                """,
                (subject_id,),
            )
            if cursor.fetchone()[0] == 0:
                from modules.mcq_builder import generate_mcqs_for_subject
                generate_mcqs_for_subject(subject_id)
                rows = _fetch_rows("AND m.status != 'archived'")

        # Find questions the student answered correctly in their most recent attempts
        recent_correct_qids = set()
        if student_id:
            cursor.execute(
                """
                SELECT sr.question_id 
                FROM student_responses sr
                JOIN student_attempts sa ON sr.attempt_id = sa.id
                WHERE sa.student_id = ? AND sa.subject_id = ? AND sr.is_correct = 1
                ORDER BY sa.created_at DESC LIMIT 50;
                """,
                (student_id, subject_id),
            )
            recent_correct_qids = {r[0] for r in cursor.fetchall()}

    if not rows:
        return []

    # Adaptive weighting: boost weak topics, down-weight recent correct
    pool_indices = list(range(len(rows)))
    weights = []
    for r in rows:
        w = 1.0
        if weak_topics and r.get("topic") in weak_topics:
            w += 2.0
        if r["id"] in recent_correct_qids:
            w *= 0.3
        weights.append(max(0.01, w))

    # Sample without replacement using calculated weights
    sample_size = min(limit, len(rows))
    chosen_indices: List[int] = []
    temp_indices = list(pool_indices)
    temp_weights = list(weights)

    for _ in range(sample_size):
        if not temp_indices:
            break
        chosen = random.choices(temp_indices, weights=temp_weights, k=1)[0]
        chosen_indices.append(chosen)
        idx_in_temp = temp_indices.index(chosen)
        temp_indices.pop(idx_in_temp)
        temp_weights.pop(idx_in_temp)

    quiz_items = []
    for idx in chosen_indices:
        row = rows[idx]
        q_id = row["id"]
        quiz_items.append({
            "question_id": q_id,
            "question_number": row["question_number"],
            "question_text": row["question_text"],
            "content_type": row["content_type"],
            "image_path": row["image_path"],
            "marks": row["marks"],
            "unit": row["unit"],
            "topic": row["topic"],
            "year": row["year"],
            "exam_type": row["exam_type"],
            "options": {
                "A": row["option_a"],
                "B": row["option_b"],
                "C": row["option_c"],
                "D": row["option_d"],
                "E": "🚫 Not in my syllabus / Skip",
            },
            "correct_option": row["correct_option"],
            "explanation": row["explanation"],
        })

    return quiz_items


def load_questions_by_ids(question_ids: List[int]) -> List[Dict[str, Any]]:
    """Loads specific questions by their question IDs using non-archived MCQs."""
    if not question_ids:
        return []
    with get_db_connection() as conn:
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(question_ids))
        query = f"""
            SELECT 
                q.id, q.question_number, q.question_text, q.content_type, 
                q.image_path, q.marks, q.unit, q.topic, p.year, p.exam_type,
                m.option_a, m.option_b, m.option_c, m.option_d, m.correct_option, m.explanation, m.status
            FROM mcq_bank m
            JOIN questions q ON m.question_id = q.id
            JOIN papers p ON q.paper_id = p.id
            WHERE q.id IN ({placeholders}) AND m.status != 'archived'
            ORDER BY CASE m.status WHEN 'verified' THEN 1 ELSE 2 END;
        """
        cursor.execute(query, tuple(question_ids))
        rows = [dict(r) for r in cursor.fetchall()]

    seen_qids = set()
    quiz_items = []
    for row in rows:
        q_id = row["id"]
        if q_id in seen_qids:
            continue
        seen_qids.add(q_id)
        quiz_items.append({
            "question_id": q_id,
            "question_number": row["question_number"],
            "question_text": row["question_text"],
            "content_type": row["content_type"],
            "image_path": row["image_path"],
            "marks": row["marks"],
            "unit": row["unit"],
            "topic": row["topic"],
            "year": row["year"],
            "exam_type": row["exam_type"],
            "options": {
                "A": row["option_a"],
                "B": row["option_b"],
                "C": row["option_c"],
                "D": row["option_d"],
                "E": "🚫 Not in my syllabus / Skip",
            },
            "correct_option": row["correct_option"],
            "explanation": row["explanation"],
        })
    return quiz_items


def load_remedial_quiz_questions(
    subject_id: int,
    weak_topics: List[str],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Loads remedial quiz questions strictly reusing stored MCQs matching the weak topics."""
    if not weak_topics:
        return load_quiz_questions(subject_id, limit=limit)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(weak_topics))
        query = f"""
            SELECT 
                q.id, q.question_number, q.question_text, q.content_type, 
                q.image_path, q.marks, q.unit, q.topic, p.year, p.exam_type,
                m.option_a, m.option_b, m.option_c, m.option_d, m.correct_option, m.explanation
            FROM mcq_bank m
            JOIN questions q ON m.question_id = q.id
            JOIN papers p ON q.paper_id = p.id
            WHERE p.subject_id = ? AND q.topic IN ({placeholders}) AND m.status != 'archived'
            ORDER BY q.marks DESC LIMIT ?;
        """
        params = [subject_id] + weak_topics + [limit]
        cursor.execute(query, tuple(params))
        rows = [dict(r) for r in cursor.fetchall()]

    if not rows:
        # Fallback to general quiz questions
        return load_quiz_questions(subject_id, limit=limit)

    quiz_items = []
    for row in rows:
        quiz_items.append({
            "question_id": row["id"],
            "question_number": row["question_number"],
            "question_text": row["question_text"],
            "content_type": row["content_type"],
            "image_path": row["image_path"],
            "marks": row["marks"],
            "unit": row["unit"],
            "topic": row["topic"],
            "year": row["year"],
            "exam_type": row["exam_type"],
            "options": {
                "A": row["option_a"],
                "B": row["option_b"],
                "C": row["option_c"],
                "D": row["option_d"],
                "E": "🚫 Not in my syllabus / Skip",
            },
            "correct_option": row["correct_option"],
            "explanation": row["explanation"],
        })

    return quiz_items


def init_quiz_session(questions: List[Dict[str, Any]]):
    """Initializes student quiz state in Streamlit."""
    st.session_state.quiz_questions = questions
    st.session_state.quiz_current_index = 0
    st.session_state.quiz_responses = {}
    st.session_state.quiz_start_time = time.time()
    st.session_state.quiz_q_start_time = time.time()
    st.session_state.quiz_completed = False


def submit_quiz_attempt(
    student_id: str,
    subject_id: int,
    quiz_type: str = "Standard",
) -> int:
    """Calculates final score and commits attempt records to the database.
    
    Excludes skipped questions from the denominator of topic accuracy.
    """
    questions = st.session_state.get("quiz_questions", [])
    responses = st.session_state.get("quiz_responses", {})

    total_valid = 0
    correct_count = 0

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Calculate score
        for idx, q in enumerate(questions):
            ans = responses.get(idx, {})
            selected = ans.get("selected_option")
            is_skipped = (selected == "E" or selected is None)
            if not is_skipped:
                total_valid += 1
                if selected == q["correct_option"]:
                    correct_count += 1

        final_percentage = round((correct_count / total_valid * 100.0), 1) if total_valid > 0 else 0.0

        # Insert attempt
        cursor.execute(
            """
            INSERT INTO student_attempts (student_id, subject_id, quiz_type, score, total_questions)
            VALUES (?, ?, ?, ?, ?);
            """,
            (student_id, subject_id, quiz_type, final_percentage, len(questions)),
        )
        attempt_id = cursor.lastrowid

        # Insert responses
        for idx, q in enumerate(questions):
            ans = responses.get(idx, {})
            selected = ans.get("selected_option")
            is_skipped = (selected == "E" or selected is None)
            is_correct = (selected == q["correct_option"]) if not is_skipped else False
            duration = ans.get("duration", 0.0)

            cursor.execute(
                """
                INSERT INTO student_responses (attempt_id, question_id, selected_option, is_correct, is_skipped, time_taken_seconds)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (attempt_id, q["question_id"], selected or "E", 1 if is_correct else 0, 1 if is_skipped else 0, duration),
            )

        conn.commit()
        return attempt_id
