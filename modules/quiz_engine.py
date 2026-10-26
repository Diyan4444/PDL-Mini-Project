import time
from typing import Any, Dict, List, Optional
import streamlit as st
from modules.database import (
    get_db_connection,
    get_mcq_by_question_id,
    add_mcq,
)


def load_quiz_questions(
    subject_id: int,
    exam_type: Optional[str] = None,
    units: Optional[List[int]] = None,
    text_only: bool = False,
    limit: int = 15,
    require_verified: bool = True,
) -> List[Dict[str, Any]]:
    """Loads and formats questions for a student quiz based on selected filters.
    
    Filters to verified MCQs by default, falling back gracefully to available MCQs
    if none have been verified yet.
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

        # Use verified filter if available or required
        status_filter = "AND m.status = 'verified'" if (verified_count > 0 and require_verified) else ""

        query = f"""
            SELECT 
                q.id, q.question_number, q.question_text, q.content_type, 
                q.image_path, q.marks, q.unit, q.topic, p.year, p.exam_type,
                m.option_a, m.option_b, m.option_c, m.option_d, m.correct_option, m.explanation
            FROM mcq_bank m
            JOIN questions q ON m.question_id = q.id
            JOIN papers p ON q.paper_id = p.id
            WHERE p.subject_id = ? {status_filter}
        """
        params = [subject_id]

        if exam_type:
            query += " AND p.exam_type = ?"
            params.append(exam_type.lower())

        if units:
            placeholders = ",".join(["?"] * len(units))
            query += f" AND q.unit IN ({placeholders})"
            params.extend(units)

        if text_only:
            query += " AND q.content_type = 'text'"

        query += " ORDER BY q.marks DESC, p.year DESC LIMIT ?;"
        params.append(limit)

        cursor.execute(query, tuple(params))
        rows = [dict(r) for r in cursor.fetchall()]

    quiz_items = []
    for row in rows:
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
            WHERE p.subject_id = ? AND q.topic IN ({placeholders})
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
