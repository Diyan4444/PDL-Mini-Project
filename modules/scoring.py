import math
from typing import Any, Dict, List, Optional
from modules.database import get_db_connection
from modules.matcher import cluster_questions_for_subject


def calculate_cluster_predictions(
    subject_id: int,
    exam_type: Optional[str] = None,
    current_year: Optional[int] = None,
    w_f: float = 0.35,
    w_r: float = 0.30,
    w_g: float = 0.20,
    w_m: float = 0.15,
    *,
    max_year_exclusive: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Calculates deterministic repetition likelihood for each question cluster
    using frequency, exponential recency decay, gap cycle analysis, and marks weight.
    
    Returns a ranked list of predicted question clusters with likelihood ratings.
    """
    # Ensure all questions under this subject are clustered
    cluster_questions_for_subject(subject_id)

    # Query all questions, papers and cluster info
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT 
                q.id as question_id, q.question_number, q.question_text, 
                q.content_type, q.image_path, q.marks, q.unit, q.topic,
                q.cluster_id, p.year, p.exam_type, p.semester
            FROM questions q
            JOIN papers p ON q.paper_id = p.id
            WHERE p.subject_id = ?
        """
        params: List[Any] = [subject_id]
        if exam_type:
            query += " AND p.exam_type = ?"
            params.append(exam_type.lower())
        if max_year_exclusive is not None:
            query += " AND p.year < ?"
            params.append(max_year_exclusive)
        
        query += " ORDER BY q.cluster_id, p.year ASC;"
        cursor.execute(query, tuple(params))
        rows = [dict(r) for r in cursor.fetchall()]

    if not rows:
        return []

    # Identify all distinct years for normalization
    distinct_years = sorted(list({r["year"] for r in rows}))
    n_years = max(1, len(distinct_years))
    max_marks_observed = max([r["marks"] for r in rows] or [10.0])

    # Determine reference year (default to next exam year after latest data year)
    if current_year is None:
        current_year = max(distinct_years) + 1

    # Group by cluster_id
    clusters: Dict[int, List[Dict[str, Any]]] = {}
    for r in rows:
        c_id = r["cluster_id"] if r["cluster_id"] is not None else r["question_id"]
        if c_id not in clusters:
            clusters[c_id] = []
        clusters[c_id].append(r)

    scored_clusters = []

    for c_id, members in clusters.items():
        years_appeared = [m["year"] for m in members]
        distinct_years_appeared = sorted(list(set(years_appeared)))
        total_appearances = len(distinct_years_appeared)

        # 1. Frequency Score (F_hat): distinct year appearances / total historical years examined
        f_hat = min(1.0, total_appearances / n_years)

        # 2. Recency Score (R_hat): exponential decay weight lambda = 0.3
        # R = sum(exp(-0.3 * (current_year - y))) over distinct years
        lambda_decay = 0.3
        recency_sum = sum(math.exp(-lambda_decay * max(0, current_year - y)) for y in distinct_years_appeared)
        # Normalize: theoretical max is if it appeared every year
        max_possible_recency = sum(math.exp(-lambda_decay * max(0, current_year - y)) for y in distinct_years) or 1.0
        r_hat = min(1.0, recency_sum / max_possible_recency)

        # 3. Gap Score (G_hat): Cyclical recurrence behavior
        # In Indian/standard university exams, a question asked 2 years ago is often repeated.
        most_recent_year = max(years_appeared)
        gap = max(0, current_year - most_recent_year)
        if gap == 1:
            # Asked just last year: often rotated out
            g_hat = 0.40
        elif gap == 2:
            # High chance of 2-year cycle repeat
            g_hat = 1.00
        elif gap == 3:
            # 3-year gap
            g_hat = 0.85
        else:
            # Unseen for 4+ years
            g_hat = 0.50

        # 4. Marks Weight (M_hat): High-weight questions (e.g. 10M/15M) are core curriculum
        avg_marks = sum(m["marks"] for m in members) / len(members)
        m_hat = min(1.0, avg_marks / max(1.0, max_marks_observed))

        # Composite Score Calculation (0.0 to 1.0)
        raw_composite = (w_f * f_hat) + (w_r * r_hat) + (w_g * g_hat) + (w_m * m_hat)
        final_score = round(raw_composite * 100.0, 1)

        # Likelihood Tier
        if final_score >= 70.0:
            likelihood = "High"
            badge_color = "#28a745"
        elif final_score >= 45.0:
            likelihood = "Medium"
            badge_color = "#ffc107"
        else:
            likelihood = "Low"
            badge_color = "#6c757d"

        # Representative metadata from the latest appearance
        representative = sorted(members, key=lambda x: x["year"], reverse=True)[0]

        scored_clusters.append({
            "cluster_id": c_id,
            "representative_question_id": representative["question_id"],
            "question_text": representative["question_text"],
            "unit": representative["unit"],
            "topic": representative["topic"],
            "content_type": representative["content_type"],
            "image_path": representative["image_path"],
            "avg_marks": round(avg_marks, 1),
            "appearances_count": total_appearances,
            "years_appeared": distinct_years_appeared,
            "gap_years": gap,
            "final_score": final_score,
            "likelihood": likelihood,
            "badge_color": badge_color,
            "frequency_score": round(f_hat * 100, 1),
            "recency_score": round(r_hat * 100, 1),
            "gap_score": round(g_hat * 100, 1),
            "marks_score": round(m_hat * 100, 1),
            "contributions": {
                "frequency": round(w_f * f_hat * 100, 1),
                "recency": round(w_r * r_hat * 100, 1),
                "gap": round(w_g * g_hat * 100, 1),
                "marks": round(w_m * m_hat * 100, 1),
            },
            "data_years": n_years,
            "low_data_warning": n_years < 3,
            "members": members,
        })

    # Sort descending by final likelihood score
    scored_clusters.sort(key=lambda x: x["final_score"], reverse=True)
    return scored_clusters
