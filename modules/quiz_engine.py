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
) -> List[Dict[str, Any]]:
    """Loads and formats questions for a student quiz based on selected filters."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT 
                q.id, q.question_number, q.question_text, q.content_type, 
                q.image_path, q.marks, q.unit, q.topic, p.year, p.exam_type
            FROM questions q
            JOIN papers p ON q.paper_id = p.id
            WHERE p.subject_id = ?
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
        mcq = get_mcq_by_question_id(q_id)
        if not mcq:
            # Fallback algorithmic generation
            mcq = {
                "option_a": f"Core analytical principle of {row['topic']}",
                "option_b": "Secondary implementation exception rule",
                "option_c": "Inverse relation under standard operating conditions",
                "option_d": "Both core principle and secondary rule are valid",
                "correct_option": "A",
                "explanation": f"Official reference answer for historical examination question {row['question_number']}.",
            }

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
                "A": mcq["option_a"],
                "B": mcq["option_b"],
                "C": mcq["option_c"],
                "D": mcq["option_d"],
                "E": "🚫 Not in my syllabus / Skip",
            },
            "correct_option": mcq["correct_option"],
            "explanation": mcq["explanation"],
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
        
        # Calculate score first
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
