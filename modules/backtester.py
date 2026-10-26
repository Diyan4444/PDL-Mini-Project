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
            "train_years": [],
            "hit_rate": 0.0,
            "recency_baseline_hit_rate": 0.0,
            "total_actual": 0,
            "hits_count": 0,
            "matched_pairs": [],
        }

    # 2. Run prediction model strictly on years < test_year without data leakage
    training_predictions = calculate_cluster_predictions(
        subject_id, current_year=test_year, max_year_exclusive=test_year
    )
    
    # Identify training years actually present in the model
    train_years_set = set()
    for pred in training_predictions:
        train_years_set.update(pred.get("years_appeared", []))
    train_years = sorted(list(train_years_set))

    if not training_predictions:
        return {
            "success": False,
            "message": f"No historical papers exist prior to {test_year} for back-testing.",
            "train_years": [],
            "hit_rate": 0.0,
            "recency_baseline_hit_rate": 0.0,
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

    # 5. Calculate naive recency baseline: rank clusters purely by latest appearance year
    recency_ranked = sorted(training_predictions, key=lambda x: max(x.get("years_appeared") or [0]), reverse=True)
    baseline_top = recency_ranked[:num_top]
    baseline_hits_count = 0
    for act_q in actual_questions:
        for b_pred in baseline_top:
            if fuzz.token_sort_ratio(act_q["question_text"], b_pred["question_text"]) >= 70.0:
                baseline_hits_count += 1
                break
    recency_baseline_hit_rate = round((baseline_hits_count / total_actual_count * 100.0), 1) if total_actual_count > 0 else 0.0

    return {
        "success": True,
        "test_year": test_year,
        "train_years": train_years,
        "total_actual": total_actual_count,
        "top_predictions_evaluated": len(top_predictions),
        "hits_count": hits_count,
        "misses_count": len(misses),
        "hit_rate": hit_rate,
        "recency_baseline_hit_rate": recency_baseline_hit_rate,
        "matched_pairs": hits,
        "missed_questions": misses,
    }


def run_rolling_backtest(subject_id: int) -> List[Dict[str, Any]]:
    """Runs historical back-testing for every year that has at least one earlier year in the dataset.
    Returns list of dicts with test_year, hit_rate, recency_baseline_hit_rate, total_actual.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT year FROM papers WHERE subject_id = ? AND year IS NOT NULL ORDER BY year ASC;",
            (subject_id,),
        )
        years = [r[0] for r in cursor.fetchall() if r[0] is not None]

    if len(years) < 2:
        return []

    results = []
    for i in range(1, len(years)):
        t_year = years[i]
        res = run_historical_backtest(subject_id, test_year=t_year)
        if res.get("success"):
            results.append({
                "test_year": t_year,
                "hit_rate": res.get("hit_rate", 0.0),
                "recency_baseline_hit_rate": res.get("recency_baseline_hit_rate", 0.0),
                "total_actual": res.get("total_actual", 0),
                "hits_count": res.get("hits_count", 0),
                "train_years": res.get("train_years", []),
            })
    return results
