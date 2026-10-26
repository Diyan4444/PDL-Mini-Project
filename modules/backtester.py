from typing import Any, Dict, List
from rapidfuzz import fuzz
from modules.database import get_db_connection
from modules.scoring import calculate_cluster_predictions


def run_historical_backtest(
    subject_id: int,
    test_year: int,
    top_percentile: float = 0.30,
) -> Dict[str, Any]:
    """Simulates past paper prediction accuracy.
    
    Predicts questions for test_year using strictly earlier papers (years < test_year),
    then checks how many actual questions from test_year appeared in the top predicted clusters.
    
    Hit Rate formula:
    (Actual Year T questions matching Top 30% predictions) / (Total questions in Year T) * 100%
    """
    # 1. Fetch actual questions that appeared in the test year
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT q.id, q.question_number, q.question_text, q.marks, q.unit, q.topic
            FROM questions q
            JOIN papers p ON q.paper_id = p.id
            WHERE p.subject_id = ? AND p.year = ?;
            """,
            (subject_id, test_year),
        )
        actual_questions = [dict(r) for r in cursor.fetchall()]

    if not actual_questions:
        return {
            "success": False,
            "message": f"No examination questions found for test year {test_year}.",
            "hit_rate": 0.0,
            "total_actual": 0,
            "hits_count": 0,
            "matched_pairs": [],
        }

    # 2. Run prediction model constrained to current_year = test_year
    # Note: calculate_cluster_predictions calculates recency and gaps relative to reference year
    all_predictions = calculate_cluster_predictions(subject_id, current_year=test_year)
    
    # Filter predictions to only those whose members appeared strictly before test_year
    training_predictions = []
    for pred in all_predictions:
        prior_members = [m for m in pred["members"] if m["year"] < test_year]
        if prior_members:
            training_predictions.append(pred)

    if not training_predictions:
        return {
            "success": False,
            "message": f"No historical papers exist prior to {test_year} for back-testing.",
            "hit_rate": 0.0,
            "total_actual": len(actual_questions),
            "hits_count": 0,
            "matched_pairs": [],
        }

    # 3. Take Top N percentile predictions
    num_top = max(1, int(len(training_predictions) * top_percentile))
    top_predictions = training_predictions[:num_top]

    # 4. Compare actual questions in test_year against top predictions using fuzzy matching
    hits = []
    misses = []

    for act_q in actual_questions:
        matched = False
        best_sim = 0.0
        best_pred = None

        for pred in top_predictions:
            sim = fuzz.token_sort_ratio(act_q["question_text"], pred["question_text"])
            if sim > best_sim:
                best_sim = sim
                best_pred = pred

        # If similarity >= 70% with a top prediction, count as a successful prediction hit
        if best_sim >= 70.0 and best_pred is not None:
            hits.append({
                "actual_question": act_q["question_text"],
                "predicted_question": best_pred["question_text"],
                "similarity": round(best_sim, 1),
                "predicted_score": best_pred["final_score"],
                "marks": act_q["marks"],
            })
        else:
            misses.append(act_q)

    total_actual_count = len(actual_questions)
    hits_count = len(hits)
    hit_rate = round((hits_count / total_actual_count * 100.0), 1) if total_actual_count > 0 else 0.0

    return {
        "success": True,
        "test_year": test_year,
        "total_actual": total_actual_count,
        "top_predictions_evaluated": len(top_predictions),
        "hits_count": hits_count,
        "misses_count": len(misses),
        "hit_rate": hit_rate,
        "matched_pairs": hits,
        "missed_questions": misses,
    }
