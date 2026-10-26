from typing import Any, Dict, List
from modules.database import get_db_connection
from modules.scoring import calculate_cluster_predictions


def analyze_attempt_performance(attempt_id: int) -> Dict[str, Any]:
    """Computes comprehensive diagnostic analysis for a specific student attempt."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Fetch attempt details
        cursor.execute(
            """
            SELECT a.*, s.name as subject_name
            FROM student_attempts a
            JOIN subjects s ON a.subject_id = s.id
            WHERE a.id = ?;
            """,
            (attempt_id,),
        )
        row = cursor.fetchone()
        if not row:
            return {"error": "Attempt not found"}
        attempt = dict(row)

        # Fetch all responses with question details
        cursor.execute(
            """
            SELECT 
                r.selected_option, r.is_correct, r.is_skipped, r.time_taken_seconds,
                q.id as question_id, q.question_number, q.question_text, q.unit, q.topic,
                q.marks, q.cluster_id, m.correct_option, m.explanation
            FROM student_responses r
            JOIN questions q ON r.question_id = q.id
            LEFT JOIN mcq_bank m ON q.id = m.question_id
            WHERE r.attempt_id = ?;
            """,
            (attempt_id,),
        )
        responses = [dict(r) for r in cursor.fetchall()]

    # Fetch likelihood predictions for this subject to correlate priority
    subject_predictions = {
        p["cluster_id"]: p["final_score"]
        for p in calculate_cluster_predictions(attempt["subject_id"])
    }

    # Topic-wise breakdowns
    topic_stats: Dict[str, Dict[str, Any]] = {}
    total_time = 0.0
    correct_count = 0
    skipped_count = 0
    mistakes_list = []
    skipped_list = []

    for r in responses:
        top = r["topic"] or f"Unit {r['unit']}"
        if top not in topic_stats:
            topic_stats[top] = {
                "unit": r["unit"],
                "total": 0,
                "correct": 0,
                "skipped": 0,
                "mistakes": 0,
                "avg_likelihood": 50.0,
            }

        total_time += r["time_taken_seconds"]

        if r["is_skipped"]:
            skipped_count += 1
            topic_stats[top]["skipped"] += 1
            skipped_list.append(r)
        else:
            topic_stats[top]["total"] += 1
            if r["is_correct"]:
                correct_count += 1
                topic_stats[top]["correct"] += 1
            else:
                topic_stats[top]["mistakes"] += 1
                mistakes_list.append(r)

    # Calculate Topic Accuracy & Revision Priority Matrix:
    # Priority = (1 - Accuracy) * Likelihood Score
    strengths = []
    weaknesses = []
    topic_summary = []
    skipped_topics = []

    for top, s in topic_stats.items():
        if s["total"] == 0:
            # All questions in this topic were skipped (out of syllabus)
            accuracy = None
            priority_index = 0.0
            all_skipped = True
            skipped_topics.append(top)
        else:
            accuracy = round(s["correct"] / s["total"] * 100.0, 1)
            all_skipped = False

        # Average predicted likelihood of related questions
        cluster_scores = [
            subject_predictions.get(r["cluster_id"], 50.0)
            for r in responses if (r["topic"] == top or f"Unit {r['unit']}" == top)
        ]
        avg_likelihood = sum(cluster_scores) / max(1, len(cluster_scores))
        
        if not all_skipped and accuracy is not None:
            # Revision priority (0 to 100)
            unmastered_ratio = 1.0 - (accuracy / 100.0)
            priority_index = round(unmastered_ratio * avg_likelihood, 1)
        else:
            priority_index = 0.0

        summary_item = {
            "topic": top,
            "unit": s["unit"],
            "total_attempted": s["total"],
            "correct": s["correct"],
            "skipped": s["skipped"],
            "accuracy": accuracy,
            "priority_score": priority_index,
            "avg_likelihood": round(avg_likelihood, 1),
            "all_skipped": all_skipped,
            "recommended_book": f"Standard Prescribed Syllabus Text (Chapter/Unit {s['unit']})",
        }
        topic_summary.append(summary_item)

        if not all_skipped and accuracy is not None:
            if accuracy >= 75.0:
                strengths.append(top)
            elif accuracy < 60.0 or s["mistakes"] > 0:
                weaknesses.append(top)

    # Sort topics by highest revision priority first
    topic_summary.sort(key=lambda x: x["priority_score"], reverse=True)

    return {
        "attempt_id": attempt_id,
        "score_percent": attempt["score"],
        "total_questions": attempt["total_questions"],
        "correct_count": correct_count,
        "skipped_count": skipped_count,
        "wrong_count": len(mistakes_list),
        "total_time_seconds": round(total_time, 1),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "topic_summary": topic_summary,
        "skipped_topics": skipped_topics,
        "mistakes": mistakes_list,
        "skipped_items": skipped_list,
    }


def get_student_history(student_id: str) -> List[Dict[str, Any]]:
    """Retrieves chronological quiz attempts for a student."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT a.*, s.name as subject_name
            FROM student_attempts a
            JOIN subjects s ON a.subject_id = s.id
            WHERE a.student_id = ?
            ORDER BY a.timestamp DESC;
            """,
            (student_id,),
        )
        return [dict(r) for r in cursor.fetchall()]
