import random
import re
from typing import Any, Dict, List, Optional
from rapidfuzz import fuzz

from modules.database import (
    get_db_connection,
    add_mcq,
)
from modules.scoring import calculate_cluster_predictions

TASK_VERB_MEANINGS = {
    "derive": "Formulate or deduce mathematically step-by-step from fundamental principles",
    "calculate": "Compute a numerical value or mathematical result using given values and formulas",
    "solve": "Determine the solution, roots, or outcome for a problem or equation",
    "explain": "Clarify principles, causes, mechanisms, or behavior with supporting reasoning",
    "define": "State the precise meaning, formal specification, or boundary of a concept",
    "differentiate": "Distinguish between two concepts by contrasting their specific characteristics",
    "draw": "Produce a clear schematic, diagram, timing chart, or architectural layout",
    "prove": "Demonstrate the mathematical or logical truth of a theorem or identity",
    "write": "Provide specific code, pseudo-code, statements, or descriptive syntax",
    "design": "Formulate an architecture, algorithm, circuit, or system structure for given requirements",
    "compare": "Examine similarities and differences between two or more items systematically",
    "discuss": "Present an analytical overview with pros, cons, and contextual applications",
    "find": "Locate or evaluate an unknown quantity, parameter, or component",
    "state": "Express concisely a formal law, property, postulate, or rule without proof",
}


def clean_question_text(text: str, watermark_phrases: Optional[List[str]] = None) -> str:
    """Strips page markers, collapses whitespace, removes common watermarks,
    and trims to at most 300 characters at a word boundary.
    """
    if not text:
        return ""
    # Strip page markers like --- Page 1 ---
    cleaned = re.sub(r"---\s*Page\s*\d+\s*---", " ", text, flags=re.IGNORECASE)
    
    if watermark_phrases:
        for wm in watermark_phrases:
            if len(wm) > 3:
                cleaned = cleaned.replace(wm, " ")

    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) > 300:
        # Cut at word boundary
        cutoff = cleaned[:300].rfind(" ")
        if cutoff > 150:
            cleaned = cleaned[:cutoff] + "..."
        else:
            cleaned = cleaned[:297] + "..."
    return cleaned


def _find_subject_watermarks(subject_questions: List[Dict[str, Any]]) -> List[str]:
    """Finds repeated n-grams appearing in >60% of questions in a subject."""
    if len(subject_questions) < 5:
        return []
    doc_count = len(subject_questions)
    # Check 3-word ngrams
    ngram_counts: Dict[str, int] = {}
    for q in subject_questions:
        words = re.findall(r"\b[A-Za-z0-9]{3,}\b", q.get("question_text", ""))
        seen_in_q = set()
        for i in range(len(words) - 2):
            tri = f"{words[i]} {words[i+1]} {words[i+2]}".lower()
            if tri not in seen_in_q:
                seen_in_q.add(tri)
                ngram_counts[tri] = ngram_counts.get(tri, 0) + 1
    
    watermarks = [ng for ng, cnt in ngram_counts.items() if (cnt / doc_count) > 0.60]
    return watermarks


def build_topic_mcq(question: Dict[str, Any], subject_questions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Generates an MCQ testing which syllabus topic the question belongs to."""
    raw_text = question.get("question_text", "")
    cleaned = clean_question_text(raw_text)
    if len(cleaned) < 20:
        return None

    correct_topic = str(question.get("topic") or "").strip()
    if not correct_topic:
        correct_topic = f"Unit {question.get('unit', 1)} Concepts"

    # Collect distinct topics from subject questions
    all_topics = {
        str(q.get("topic") or "").strip()
        for q in subject_questions
        if str(q.get("topic") or "").strip() and str(q.get("topic") or "").strip() != correct_topic
    }

    # If fewer than 3 other topics, fall back to unit labels
    candidate_distractors = list(all_topics)
    if len(candidate_distractors) < 3:
        for u in range(1, 6):
            u_label = f"Unit {u} Core Topics"
            if u_label != correct_topic and u_label not in candidate_distractors:
                candidate_distractors.append(u_label)

    if len(candidate_distractors) < 3:
        return None

    # Pick 3 distractors with lowest token_sort_ratio to correct topic to avoid near-duplicates
    ranked_distractors = sorted(
        candidate_distractors,
        key=lambda d: fuzz.token_sort_ratio(correct_topic, d)
    )
    chosen_distractors = ranked_distractors[:3]

    q_id = question.get("id", 0)
    rng = random.Random(f"{q_id}:topic")
    raw_opts = [("correct", correct_topic)] + [("dist", d) for d in chosen_distractors]
    rng.shuffle(raw_opts)

    letters = ["A", "B", "C", "D"]
    opt_map = {}
    correct_letter = "A"
    for ltr, (kind, txt) in zip(letters, raw_opts):
        opt_map[f"option_{ltr.lower()}"] = txt
        if kind == "correct":
            correct_letter = ltr

    stem = f"Which topic does the following exam question belong to?\n\"{cleaned}\""
    return {
        "question_id": q_id,
        "option_a": opt_map["option_a"],
        "option_b": opt_map["option_b"],
        "option_c": opt_map["option_c"],
        "option_d": opt_map["option_d"],
        "correct_option": correct_letter,
        "explanation": f"This question directly addresses curriculum components of '{correct_topic}'.",
        "generator": "rule_based_topic",
        "stem": stem,
    }


def build_task_mcq(question: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generates an MCQ identifying the core cognitive task/command verb required."""
    raw_text = question.get("question_text", "")
    cleaned = clean_question_text(raw_text)
    if len(cleaned) < 20:
        return None

    # Detect command verb
    matched_verb = None
    for verb in TASK_VERB_MEANINGS:
        if re.search(rf"\b{verb}\b", cleaned, re.IGNORECASE):
            matched_verb = verb
            break

    if not matched_verb:
        return None

    correct_meaning = TASK_VERB_MEANINGS[matched_verb]
    other_verbs = [v for v in TASK_VERB_MEANINGS if v != matched_verb]
    q_id = question.get("id", 0)
    rng = random.Random(f"{q_id}:task")
    chosen_distractor_verbs = rng.sample(other_verbs, 3)
    distractor_meanings = [TASK_VERB_MEANINGS[v] for v in chosen_distractor_verbs]

    raw_opts = [("correct", correct_meaning)] + [("dist", m) for m in distractor_meanings]
    rng.shuffle(raw_opts)

    letters = ["A", "B", "C", "D"]
    opt_map = {}
    correct_letter = "A"
    for ltr, (kind, txt) in zip(letters, raw_opts):
        opt_map[f"option_{ltr.lower()}"] = txt
        if kind == "correct":
            correct_letter = ltr

    stem = f"What is the primary examination task asked in this question?\n\"{cleaned}\""
    return {
        "question_id": q_id,
        "option_a": opt_map["option_a"],
        "option_b": opt_map["option_b"],
        "option_c": opt_map["option_c"],
        "option_d": opt_map["option_d"],
        "correct_option": correct_letter,
        "explanation": f"The question starts with or centers on the directive '{matched_verb.upper()}', requiring the student to: {correct_meaning.lower()}.",
        "generator": "rule_based_task",
        "stem": stem,
    }


def build_repeat_mcq(cluster: Dict[str, Any], all_subject_years: List[int]) -> Optional[Dict[str, Any]]:
    """Generates an MCQ testing historical repeat recognition for recurring clusters."""
    years = cluster.get("years_appeared", [])
    if len(years) < 2:
        return None

    correct_str = ", ".join(str(y) for y in sorted(years))
    q_id = cluster.get("representative_question_id", 0)
    q_text = clean_question_text(cluster.get("question_text", ""))
    if len(q_text) < 20:
        return None

    # Distractor year sets
    rng = random.Random(f"{q_id}:repeat")
    distractors = set()
    attempts = 0
    while len(distractors) < 3 and attempts < 20:
        attempts += 1
        d_len = len(years)
        # Shift or sample years
        offset = rng.choice([-3, -2, -1, 1, 2, 3])
        cand = sorted(list({y + offset for y in years if (y + offset) > 2000}))
        cand_str = ", ".join(str(y) for y in cand)
        if cand_str != correct_str and len(cand) == d_len:
            distractors.add(cand_str)
    
    if len(distractors) < 3:
        # Fall back to synthetic plausible combinations
        base = min(years)
        for delta in [1, 2, 3]:
            fake = f"{base - delta}, {base + delta}"
            if fake != correct_str:
                distractors.add(fake)
            if len(distractors) == 3:
                break

    if len(distractors) < 3:
        return None

    raw_opts = [("correct", correct_str)] + [("dist", d) for d in list(distractors)[:3]]
    rng.shuffle(raw_opts)

    letters = ["A", "B", "C", "D"]
    opt_map = {}
    correct_letter = "A"
    for ltr, (kind, txt) in zip(letters, raw_opts):
        opt_map[f"option_{ltr.lower()}"] = txt
        if kind == "correct":
            correct_letter = ltr

    stem = f"In which examination year(s) has this repeated topic/question appeared historically?\n\"{q_text}\""
    return {
        "question_id": q_id,
        "option_a": opt_map["option_a"],
        "option_b": opt_map["option_b"],
        "option_c": opt_map["option_c"],
        "option_d": opt_map["option_d"],
        "correct_option": correct_letter,
        "explanation": f"According to historical paper records, this question cluster appeared in: {correct_str}.",
        "generator": "rule_based_repeat",
        "stem": stem,
    }


def generate_mcqs_for_subject(subject_id: int) -> Dict[str, int]:
    """Generates rule-based draft MCQs (topic, task, and repeat) for questions without active MCQs."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Fetch all questions for this subject
        cursor.execute(
            """
            SELECT q.*, p.year
            FROM questions q
            JOIN papers p ON q.paper_id = p.id
            WHERE p.subject_id = ?
            ORDER BY q.id ASC;
            """,
            (subject_id,),
        )
        questions = [dict(r) for r in cursor.fetchall()]

        # Questions that already have non-archived MCQs
        cursor.execute(
            """
            SELECT DISTINCT m.question_id 
            FROM mcq_bank m
            JOIN questions q ON m.question_id = q.id
            JOIN papers p ON q.paper_id = p.id
            WHERE p.subject_id = ? AND m.status != 'archived';
            """,
            (subject_id,),
        )
        existing_mcq_qids = {r[0] for r in cursor.fetchall()}

    if not questions:
        return {"created": 0, "skipped": 0}

    watermarks = _find_subject_watermarks(questions)
    clusters = calculate_cluster_predictions(subject_id)
    cluster_by_repid = {c["representative_question_id"]: c for c in clusters}
    all_subject_years = sorted(list({q["year"] for q in questions if q.get("year")}))

    created_count = 0
    skipped_count = 0

    for q in questions:
        q_id = q["id"]
        if q_id in existing_mcq_qids:
            continue

        raw_text = clean_question_text(q.get("question_text", ""), watermarks)
        if len(raw_text) < 20:
            skipped_count += 1
            continue

        mcq_payload = None

        # Strategy 1: If question is a recurring cluster representative, create repeat MCQ
        if q_id in cluster_by_repid and len(cluster_by_repid[q_id].get("years_appeared", [])) >= 2:
            mcq_payload = build_repeat_mcq(cluster_by_repid[q_id], all_subject_years)

        # Strategy 2: If question has task command verb, create task MCQ
        if not mcq_payload:
            mcq_payload = build_task_mcq(q)

        # Strategy 3: Default to topic MCQ
        if not mcq_payload:
            mcq_payload = build_topic_mcq(q, questions)

        if mcq_payload:
            add_mcq(
                question_id=q_id,
                option_a=mcq_payload["option_a"],
                option_b=mcq_payload["option_b"],
                option_c=mcq_payload["option_c"],
                option_d=mcq_payload["option_d"],
                correct_option=mcq_payload["correct_option"],
                explanation=mcq_payload["explanation"],
                status="draft",
                generator=mcq_payload["generator"],
            )
            created_count += 1
        else:
            skipped_count += 1

    return {"created": created_count, "skipped": skipped_count}
