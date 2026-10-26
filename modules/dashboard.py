from typing import Any, Dict, List, Optional
from modules.database import get_db_connection
from modules.scoring import calculate_cluster_predictions


def get_overview_stats(subject_id: Optional[int] = None) -> Dict[str, Any]:
    """Computes high-level aggregated metrics across subjects, papers, questions, and MCQs."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Counts of subjects, papers, questions
        if subject_id:
            cursor.execute("SELECT COUNT(*) FROM subjects WHERE id = ?;", (subject_id,))
            subjects_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM papers WHERE subject_id = ?;", (subject_id,))
            papers_count = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT COUNT(q.id) FROM questions q
                JOIN papers p ON q.paper_id = p.id
                WHERE p.subject_id = ?;
                """,
                (subject_id,),
            )
            questions_count = cursor.fetchone()[0]
            cursor.execute(
                "SELECT DISTINCT year FROM papers WHERE subject_id = ? AND year IS NOT NULL;",
                (subject_id,),
            )
            distinct_years = [r[0] for r in cursor.fetchall()]

            cursor.execute(
                """
                SELECT m.status, COUNT(m.id) 
                FROM mcq_bank m
                JOIN questions q ON m.question_id = q.id
                JOIN papers p ON q.paper_id = p.id
                WHERE p.subject_id = ?
                GROUP BY m.status;
                """,
                (subject_id,),
            )
            mcq_status_counts = {r[0]: r[1] for r in cursor.fetchall()}

            cursor.execute(
                """
                SELECT AVG(quality_score), AVG(metadata_confidence) 
                FROM papers WHERE subject_id = ?;
                """,
                (subject_id,),
            )
            avg_q, avg_conf = cursor.fetchone()

            cursor.execute(
                """
                SELECT q.unit, COUNT(q.id) 
                FROM questions q
                JOIN papers p ON q.paper_id = p.id
                WHERE p.subject_id = ?
                GROUP BY q.unit ORDER BY q.unit ASC;
                """,
                (subject_id,),
            )
            unit_q_counts = {f"Unit {r[0]}": r[1] for r in cursor.fetchall()}
        else:
            cursor.execute("SELECT COUNT(*) FROM subjects;")
            subjects_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM papers;")
            papers_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM questions;")
            questions_count = cursor.fetchone()[0]
            cursor.execute("SELECT DISTINCT year FROM papers WHERE year IS NOT NULL;")
            distinct_years = [r[0] for r in cursor.fetchall()]

            cursor.execute("SELECT status, COUNT(id) FROM mcq_bank GROUP BY status;")
            mcq_status_counts = {r[0]: r[1] for r in cursor.fetchall()}

            cursor.execute("SELECT AVG(quality_score), AVG(metadata_confidence) FROM papers;")
            avg_q, avg_conf = cursor.fetchone()

            cursor.execute("SELECT unit, COUNT(id) FROM questions GROUP BY unit ORDER BY unit ASC;")
            unit_q_counts = {f"Unit {r[0]}": r[1] for r in cursor.fetchall()}

    # Top predictions if a subject is available
    top_predictions: List[Dict[str, Any]] = []
    unit_avg_likelihood: Dict[str, float] = {}

    target_subj = subject_id
    if not target_subj:
        # Pick the first subject if available
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM subjects ORDER BY id ASC LIMIT 1;")
            first_s = c.fetchone()
            if first_s:
                target_subj = first_s[0]

    if target_subj:
        all_preds = calculate_cluster_predictions(target_subj)
        top_predictions = all_preds[:5]

        unit_scores: Dict[int, List[float]] = {}
        for p in all_preds:
            u = p.get("unit", 1)
            unit_scores.setdefault(u, []).append(p.get("final_score", 0.0))
        for u in sorted(unit_scores.keys()):
            scores = unit_scores[u]
            unit_avg_likelihood[f"Unit {u}"] = round(sum(scores) / max(1, len(scores)), 1)

    return {
        "subjects_count": subjects_count,
        "papers_count": papers_count,
        "questions_count": questions_count,
        "distinct_years_count": len(distinct_years),
        "distinct_years": sorted(distinct_years),
        "mcqs_verified": mcq_status_counts.get("verified", 0),
        "mcqs_draft": mcq_status_counts.get("draft", 0),
        "mcqs_archived": mcq_status_counts.get("archived", 0),
        "avg_quality_score": round(float(avg_q or 0.0), 2),
        "avg_metadata_confidence": round(float(avg_conf or 0.0), 2),
        "questions_per_unit": unit_q_counts,
        "unit_avg_likelihood": unit_avg_likelihood,
        "top_predictions": top_predictions,
    }
