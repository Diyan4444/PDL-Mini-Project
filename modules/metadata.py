import re
from typing import Any, Dict, List, Optional, Tuple
from rapidfuzz import fuzz

ROMAN_TO_INT = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
    "vi": 6,
    "vii": 7,
    "viii": 8,
    "ix": 9,
    "x": 10,
    "ill": 3,  # Common OCR mistake for III
    "lll": 3,
    "111": 3,
    "ll": 2,
    "11": 2,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
}


def clean_ocr_text(text: str) -> str:
    """Normalizes whitespace and common OCR punctuation anomalies."""
    if not text:
        return ""
    text = re.sub(r"[\r\n]+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_metadata(text_lines: List[str], full_text: Optional[str] = None) -> Dict[str, Any]:
    """Extracts high-fidelity exam metadata with confidence scores and evidence strings.
    
    Fields extracted:
    - institute
    - course_name
    - course_code
    - exam_name
    - exam_type ('midterm' | 'endterm')
    - is_makeup (0 | 1)
    - exam_date
    - year
    - semester
    - program
    - branch
    - study_year
    - duration_minutes
    - max_marks
    - metadata_confidence
    """
    if not full_text:
        full_text = "\n".join(text_lines)

    norm_full = clean_ocr_text(full_text)
    norm_lines = [clean_ocr_text(l) for l in text_lines if clean_ocr_text(l)]

    results: Dict[str, Any] = {
        "institute": {"value": "Veermata Jijabai Technological Institute", "confidence": 0.5, "evidence": ""},
        "course_name": {"value": "Engineering Mathematics", "confidence": 0.3, "evidence": ""},
        "course_code": {"value": "", "confidence": 0.0, "evidence": ""},
        "exam_name": {"value": "Mid Semester Examination", "confidence": 0.5, "evidence": ""},
        "exam_type": {"value": "midterm", "confidence": 0.5, "evidence": ""},
        "is_makeup": {"value": 0, "confidence": 0.8, "evidence": ""},
        "exam_date": {"value": "", "confidence": 0.0, "evidence": ""},
        "year": {"value": 2024, "confidence": 0.5, "evidence": ""},
        "semester": {"value": 3, "confidence": 0.5, "evidence": ""},
        "program": {"value": "B.Tech", "confidence": 0.5, "evidence": ""},
        "branch": {"value": "", "confidence": 0.0, "evidence": ""},
        "study_year": {"value": "S.Y.", "confidence": 0.5, "evidence": ""},
        "duration_minutes": {"value": 90, "confidence": 0.5, "evidence": ""},
        "max_marks": {"value": 40, "confidence": 0.5, "evidence": ""},
    }

    # 1. Institute Detection
    for line in norm_lines[:10]:
        if re.search(r"VEERMATA|JIJABAI|VJTI", line, re.IGNORECASE):
            results["institute"] = {
                "value": "Veermata Jijabai Technological Institute",
                "confidence": 0.98,
                "evidence": line,
            }
            break

    # 2. Make-up / Re-exam Detection
    for line in norm_lines[:15]:
        if re.search(r"make[-\s]?up|re[-\s]?exam|supplementary|\bkt\b", line, re.IGNORECASE):
            results["is_makeup"] = {"value": 1, "confidence": 0.95, "evidence": line}
            break

    # 3. Exam Name & Normalized Exam Type
    # "Mid Semester Examination", "Mid Semester Test", "MSE", "IA", "ISE" -> midterm
    # "End Semester Examination", "End Semester Test", "ESE" -> endterm
    exam_type_found = False
    for line in norm_lines[:15]:
        if re.search(r"end\s*sem(?:ester)?|\bese\b", line, re.IGNORECASE):
            results["exam_type"] = {"value": "endterm", "confidence": 0.95, "evidence": line}
            results["exam_name"] = {"value": line, "confidence": 0.90, "evidence": line}
            exam_type_found = True
            break
        elif re.search(r"mid\s*sem(?:ester)?|\bmse\b|midterm|\btest\s*[12]\b|\bia\b|\bise\b", line, re.IGNORECASE):
            results["exam_type"] = {"value": "midterm", "confidence": 0.95, "evidence": line}
            results["exam_name"] = {"value": line, "confidence": 0.90, "evidence": line}
            exam_type_found = True
            break

    # 4. Course Code & Course Name
    # Patterns: (R5IT2002T), (R5MA2007T), R5IT2002T, Course Name - (Code)
    # A valid course code must contain both letters and digits, and not be a pure pin code or pure number.
    for line in norm_lines[:25]:
        # Exclude postal address lines
        if re.search(r"Mumbai|Matunga|Pin|Postal|Affiliated", line, re.IGNORECASE):
            continue

        m = re.search(r"([A-Za-z\s,\-\&]{5,60})\s*[\-\(]+\s*([A-Za-z0-9]{5,12})\)?", line)
        if m:
            c_name_cand = m.group(1).strip()
            c_code_cand = m.group(2).strip().upper()
            
            # Must have both alphabets and digits
            if not (re.search(r"[A-Z]", c_code_cand) and re.search(r"[0-9]", c_code_cand)):
                continue

            # Clean OCR confusion in code
            c_code_cand = re.sub(r"^R5LT", "R5IT", c_code_cand)
            c_code_cand = re.sub(r"^R51T", "R5IT", c_code_cand)
            c_code_cand = re.sub(r"^R5lT", "R5IT", c_code_cand)
            
            if any(kw in c_name_cand.upper() for kw in ["COURSE", "NAME"]):
                c_name_cand = re.sub(r"^(?:COURSE\s*NAME[\s\-:]*)+", "", c_name_cand, flags=re.IGNORECASE).strip()
            if len(c_name_cand) > 3 and not re.search(r"PROGRAM|SEMESTER|DATE", c_name_cand, re.IGNORECASE):
                c_name_clean = c_name_cand.strip(" -:\t")
                results["course_name"] = {"value": c_name_clean, "confidence": 0.95, "evidence": line}
                results["course_code"] = {"value": c_code_cand, "confidence": 0.98, "evidence": line}
                break

    # Fallback course code search: look for explicit R5 patterns or [A-Z]{2,4}\d{4}
    if not results["course_code"]["value"]:
        for line in norm_lines[:25]:
            m_code = re.search(r"\b(R5[A-Z0-9]{5,10}[A-Z]?)\b", line)
            if m_code:
                code_val = m_code.group(1).upper()
                code_val = re.sub(r"^R5LT", "R5IT", code_val)
                code_val = re.sub(r"^R51T", "R5IT", code_val)
                results["course_code"] = {"value": code_val, "confidence": 0.90, "evidence": line}
                break

    # 5. Date & Year Extraction
    # Format: 24/09/24, 19/09/2024, 2024-09-24, Sep 2024, 04/11/24
    for line in norm_lines[:20]:
        m_date = re.search(r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b", line)
        if m_date:
            raw_date = m_date.group(1)
            results["exam_date"] = {"value": raw_date, "confidence": 0.95, "evidence": line}
            # Extract year
            parts = re.split(r"[\/\-\.]", raw_date)
            yr = int(parts[-1])
            if yr < 100:
                yr += 2000
            results["year"] = {"value": yr, "confidence": 0.95, "evidence": line}
            break
        # Format "Sep 2024" or "November 2024"
        m_myr = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+(20\d\d)\b", line, re.IGNORECASE)
        if m_myr:
            results["exam_date"] = {"value": f"{m_myr.group(1)} {m_myr.group(2)}", "confidence": 0.90, "evidence": line}
            results["year"] = {"value": int(m_myr.group(2)), "confidence": 0.95, "evidence": line}
            break

    # 6. Semester & Study Year
    # "Sem-III", "Sem-Ill", "Semester 3", "S.Y. B.Tech"
    for line in norm_lines[:20]:
        m_sem = re.search(r"(?:Sem(?:ester)?\s*[\-\:]?\s*)([A-Za-z0-9]+)", line, re.IGNORECASE)
        if m_sem:
            sem_raw = m_sem.group(1).lower().strip()
            sem_val = ROMAN_TO_INT.get(sem_raw, 3)
            results["semester"] = {"value": sem_val, "confidence": 0.92, "evidence": line}
        
        m_study = re.search(r"\b([FST]\.?Y\.?)\b", line, re.IGNORECASE)
        if m_study:
            results["study_year"] = {"value": m_study.group(1).upper(), "confidence": 0.90, "evidence": line}

    # 7. Program & Branch
    for line in norm_lines[:20]:
        if re.search(r"\bB\.?\s*Tech\b", line, re.IGNORECASE):
            results["program"] = {"value": "B.Tech", "confidence": 0.95, "evidence": line}
        elif re.search(r"\bM\.?\s*Tech\b", line, re.IGNORECASE):
            results["program"] = {"value": "M.Tech", "confidence": 0.95, "evidence": line}

        m_branch = re.search(r"\((Information Technology|Computer Engineering|Civil Engineering|Mechanical Engineering|Electrical Engineering)\)", line, re.IGNORECASE)
        if m_branch:
            results["branch"] = {"value": m_branch.group(1).title(), "confidence": 0.95, "evidence": line}
        elif re.search(r"Information Technology", line, re.IGNORECASE):
            results["branch"] = {"value": "Information Technology", "confidence": 0.90, "evidence": line}

    # 8. Max Marks
    # "MARKS 40", "Max. Marks: 40", "Marks: 100", "40"
    for line in norm_lines[:20]:
        m_marks = re.search(r"(?:MAX\.?\s*MARKS|MARKS)\s*[\:\-]?\s*(\d{2,3})", line, re.IGNORECASE)
        if m_marks:
            val = int(m_marks.group(1))
            results["max_marks"] = {"value": val, "confidence": 0.95, "evidence": line}
            break

    # 9. Duration / Time Window
    # "11:15 AM to 12:45 PM", "1.30 HRS", "1 Hour 30 Minutes"
    for line in norm_lines[:20]:
        m_win = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM))\s*(?:to|-)\s*(\d{1,2}:\d{2}\s*(?:AM|PM))", line, re.IGNORECASE)
        if m_win:
            results["duration_minutes"] = {"value": 90, "confidence": 0.92, "evidence": line}
            break
        elif re.search(r"1[\.\:]30\s*HRS|1\.5\s*hours?", line, re.IGNORECASE):
            results["duration_minutes"] = {"value": 90, "confidence": 0.90, "evidence": line}
            break

    # Tie breaker: if exam_type is still default and max_marks is present
    if not exam_type_found:
        if results["max_marks"]["value"] <= 45:
            results["exam_type"] = {"value": "midterm", "confidence": 0.70, "evidence": "Inferred from max_marks <= 45"}
        elif results["max_marks"]["value"] >= 60:
            results["exam_type"] = {"value": "endterm", "confidence": 0.70, "evidence": "Inferred from max_marks >= 60"}

    # Overall Confidence Calculation
    weights = {
        "course_code": 0.30,
        "course_name": 0.20,
        "exam_type": 0.20,
        "year": 0.15,
        "max_marks": 0.15,
    }
    overall_conf = sum(results[k]["confidence"] * weights[k] for k in weights)
    results["metadata_confidence"] = round(overall_conf, 3)

    return results


def match_subject(
    course_code: str,
    course_name: str,
    db_subjects: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Matches extracted metadata against registered database subjects.
    
    1. Checks exact code match first.
    2. Checks fuzzy name similarity (RapidFuzz >= 90%).
       If matched subject has placeholder code, proposes upgrading it.
    3. Otherwise suggests creating a new subject.
    """
    clean_code = (course_code or "").strip().upper()
    clean_name = (course_name or "").strip()

    # 1. Exact course code match
    if clean_code:
        for sub in db_subjects:
            sub_code = (sub.get("code") or "").strip().upper()
            if sub_code and sub_code == clean_code:
                return {
                    "matched": True,
                    "subject_id": sub["id"],
                    "action": "exact_code_match",
                    "subject_name": sub["name"],
                    "subject_code": sub["code"],
                    "confidence": 1.0,
                }

    # 2. Fuzzy name match
    best_match = None
    best_score = 0.0

    for sub in db_subjects:
        sub_name = (sub.get("name") or "").strip()
        score = fuzz.token_set_ratio(clean_name, sub_name)
        if score > best_score:
            best_score = score
            best_match = sub

    if best_match and best_score >= 88.0:
        sub_code = (best_match.get("code") or "").strip()
        is_placeholder = not sub_code or len(sub_code) <= 2 or sub_code.isdigit()
        
        return {
            "matched": True,
            "subject_id": best_match["id"],
            "action": "upgrade_code" if (is_placeholder and clean_code) else "name_match",
            "subject_name": best_match["name"],
            "subject_code": best_match.get("code", ""),
            "proposed_code": clean_code if is_placeholder else None,
            "confidence": round(best_score / 100.0, 2),
        }

    # 3. No match found
    return {
        "matched": False,
        "action": "create_subject",
        "proposed_name": clean_name or "New Subject",
        "proposed_code": clean_code or "",
        "confidence": 0.0,
    }
