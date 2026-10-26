import re
from typing import Dict, List
from rapidfuzz import fuzz
from modules.database import get_db_connection


def clean_text_for_matching(text: str) -> str:
    """Standardizes text string by lowercasing, stripping punctuation and redundant whitespace."""
    text_clean = text.lower()
    text_clean = re.sub(r"[^\w\s]", " ", text_clean)
    text_clean = re.sub(r"\s+", " ", text_clean).strip()
    return text_clean


def cluster_questions_for_subject(
    subject_id: int,
    similarity_threshold: float = 85.0
) -> Dict[int, int]:
    """Clusters all questions under a subject into repeat groups using RapidFuzz and diagram group IDs.
    
    Returns a dictionary mapping question_id -> assigned_cluster_id.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT q.id, q.question_text, q.diagram_group_id, q.cluster_id
            FROM questions q
            JOIN papers p ON q.paper_id = p.id
            WHERE p.subject_id = ?
            ORDER BY p.year ASC, q.id ASC;
            """,
            (subject_id,),
        )
        rows = [dict(r) for r in cursor.fetchall()]

    if not rows:
        return {}

    # Read existing max cluster_id
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(cluster_id) FROM questions;")
        max_existing = cursor.fetchone()[0]
        next_cluster_id = (max_existing if max_existing is not None else 0) + 1

    # Pre-clean strings
    cleaned_texts = {r["id"]: clean_text_for_matching(r["question_text"]) for r in rows}
    
    # Store clusters: cluster_id -> list of member question dicts
    cluster_members: Dict[int, List[Dict]] = {}
    q_to_cluster: Dict[int, int] = {}

    for row in rows:
        q_id = row["id"]
        q_clean = cleaned_texts[q_id]
        diag_grp = row.get("diagram_group_id")
        
        matched_cluster = None

        # 1. First priority: Check if diagram group matches an existing cluster
        if diag_grp is not None:
            for c_id, members in cluster_members.items():
                if any(m.get("diagram_group_id") == diag_grp for m in members):
                    matched_cluster = c_id
                    break

        # 2. Second priority: Fuzzy text match against cluster representatives
        if matched_cluster is None and len(q_clean) > 12:
            best_score = 0.0
            best_candidate_cluster = None
            for c_id, members in cluster_members.items():
                # Compare against the first/representative question of the cluster
                rep_clean = cleaned_texts[members[0]["id"]]
                sim = fuzz.token_sort_ratio(q_clean, rep_clean)
                if sim >= similarity_threshold and sim > best_score:
                    best_score = sim
                    best_candidate_cluster = c_id
            
            if best_candidate_cluster is not None:
                matched_cluster = best_candidate_cluster

        # 3. If no match found, create a new cluster
        if matched_cluster is None:
            # Preserve existing cluster_id if already assigned in previous run
            if row.get("cluster_id"):
                matched_cluster = row["cluster_id"]
            else:
                matched_cluster = next_cluster_id
                next_cluster_id += 1

        if matched_cluster not in cluster_members:
            cluster_members[matched_cluster] = []
        cluster_members[matched_cluster].append(row)
        q_to_cluster[q_id] = matched_cluster

    # Persist updated cluster_ids back to the database
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for q_id, c_id in q_to_cluster.items():
            cursor.execute("UPDATE questions SET cluster_id = ? WHERE id = ?;", (c_id, q_id))
        conn.commit()

    return q_to_cluster
