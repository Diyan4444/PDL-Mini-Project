import json
import os
import shutil
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "exam_predictor.db")

DEFAULT_TAGS = [
    ("draw", "task"),
    ("diagram", "content"),
    ("graph", "content"),
    ("derive", "task"),
    ("calculate", "task"),
    ("explain", "task"),
    ("define", "task"),
    ("differentiate", "task"),
    ("code", "content"),
    ("architecture", "topic"),
    ("short-note", "task"),
    ("numerical", "task"),
]


def get_db_connection() -> sqlite3.Connection:
    """Creates a connection to the SQLite database with WAL mode enabled."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db():
    """Initializes the relational SQLite database with the full production schema
    and applies additive migrations safely without dropping any tables.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 0. Source Files (Combined PDF parent sources)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS source_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sha256 TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                page_count INTEGER NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 1. Subjects
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 2. Papers
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                semester INTEGER NOT NULL,
                exam_type TEXT NOT NULL CHECK(exam_type IN ('midterm', 'endterm')),
                file_hash TEXT NOT NULL UNIQUE,
                file_path TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            """
        )

        # 3. Diagram Groups
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS diagram_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_uid TEXT NOT NULL UNIQUE,
                representative_phash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 4. Questions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                question_number TEXT NOT NULL,
                question_text TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT 'text',
                image_path TEXT,
                phash TEXT,
                diagram_group_id INTEGER,
                marks REAL DEFAULT 5.0,
                unit INTEGER DEFAULT 1,
                topic TEXT DEFAULT 'General',
                confidence_score REAL DEFAULT 1.0,
                is_reviewed BOOLEAN DEFAULT 0,
                cluster_id INTEGER,
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
                FOREIGN KEY (diagram_group_id) REFERENCES diagram_groups(id) ON DELETE SET NULL
            );
            """
        )

        # 5. Tags
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL DEFAULT 'task',
                is_active BOOLEAN DEFAULT 1
            );
            """
        )

        # 6. Question Tags
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS question_tags (
                question_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (question_id, tag_id),
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            );
            """
        )

        # 7. MCQ Bank
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS mcq_bank (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option TEXT NOT NULL CHECK(correct_option IN ('A', 'B', 'C', 'D')),
                explanation TEXT NOT NULL,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            );
            """
        )

        # 8. Student Attempts
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS student_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                subject_id INTEGER NOT NULL,
                quiz_type TEXT NOT NULL,
                score REAL NOT NULL,
                total_questions INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            """
        )

        # 9. Student Responses
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS student_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                selected_option TEXT,
                is_correct BOOLEAN DEFAULT 0,
                is_skipped BOOLEAN DEFAULT 0,
                time_taken_seconds REAL DEFAULT 0.0,
                FOREIGN KEY (attempt_id) REFERENCES student_attempts(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            );
            """
        )

        # 10. Audit Log
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Seed initial tags if empty
        cursor.execute("SELECT COUNT(*) FROM tags;")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT OR IGNORE INTO tags (name, category, is_active) VALUES (?, ?, 1);",
                DEFAULT_TAGS,
            )

        # --- SAFE ADDITIVE MIGRATIONS (Guarded by PRAGMA table_info) ---
        # A. Papers columns
        cursor.execute("PRAGMA table_info(papers);")
        existing_paper_cols = {row["name"] for row in cursor.fetchall()}
        paper_additions = [
            ("source_file_id", "INTEGER REFERENCES source_files(id)"),
            ("page_start", "INTEGER"),
            ("page_end", "INTEGER"),
            ("course_code", "TEXT"),
            ("course_name_raw", "TEXT"),
            ("exam_name_raw", "TEXT"),
            ("exam_date", "TEXT"),
            ("program", "TEXT"),
            ("branch", "TEXT"),
            ("study_year", "TEXT"),
            ("duration_minutes", "INTEGER"),
            ("max_marks", "INTEGER"),
            ("is_makeup", "INTEGER DEFAULT 0"),
            ("quality_score", "REAL"),
            ("metadata_confidence", "REAL"),
            ("status", "TEXT DEFAULT 'accepted'"),
        ]
        for col_name, col_type in paper_additions:
            if col_name not in existing_paper_cols:
                cursor.execute(f"ALTER TABLE papers ADD COLUMN {col_name} {col_type};")

        # B. Questions columns
        cursor.execute("PRAGMA table_info(questions);")
        existing_q_cols = {row["name"] for row in cursor.fetchall()}
        question_additions = [
            ("parent_question_number", "INTEGER"),
            ("part_label", "TEXT"),
            ("co_tag", "TEXT"),
            ("page_no", "INTEGER"),
            ("bbox_json", "TEXT"),
            ("is_continuation", "INTEGER DEFAULT 0"),
            ("figure_path", "TEXT"),
            ("figure_phash", "TEXT"),
        ]
        for col_name, col_type in question_additions:
            if col_name not in existing_q_cols:
                cursor.execute(f"ALTER TABLE questions ADD COLUMN {col_name} {col_type};")

        # C. MCQ Bank status column
        cursor.execute("PRAGMA table_info(mcq_bank);")
        existing_mcq_cols = {row["name"] for row in cursor.fetchall()}
        if "status" not in existing_mcq_cols:
            cursor.execute("ALTER TABLE mcq_bank ADD COLUMN status TEXT DEFAULT 'draft';")

        conn.commit()


def log_action(actor: str, action: str, details: str = ""):
    """Records an audit log entry for system actions."""
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO audit_log (actor, action, details) VALUES (?, ?, ?);",
            (actor, action, details),
        )
        conn.commit()


# Source Files Helpers
def add_source_file(sha256: str, filename: str, path: str, page_count: int) -> int:
    """Stores a source PDF record, returning its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO source_files (sha256, filename, path, page_count)
            VALUES (?, ?, ?, ?);
            """,
            (sha256, filename, path, int(page_count)),
        )
        conn.commit()
        cursor.execute("SELECT id FROM source_files WHERE sha256 = ?;", (sha256,))
        row = cursor.fetchone()
        return row["id"] if row else 0


def get_source_file_by_hash(sha256: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM source_files WHERE sha256 = ?;", (sha256,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_source_files() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM source_files ORDER BY uploaded_at DESC;")
        return [dict(row) for row in cursor.fetchall()]


# Subject Helpers
def get_all_subjects() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subjects ORDER BY name ASC;")
        return [dict(row) for row in cursor.fetchall()]


def get_subject_by_id(subject_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subjects WHERE id = ?;", (subject_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_subject_by_code(code: str) -> Optional[Dict[str, Any]]:
    if not code:
        return None
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subjects WHERE LOWER(code) = LOWER(?);", (code.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_subject(name: str, code: str = "") -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO subjects (name, code) VALUES (?, ?);",
            (name.strip(), code.strip()),
        )
        conn.commit()
        return cursor.lastrowid


def update_subject(subject_id: int, name: str, code: str = "") -> bool:
    """Updates the name and syllabus code of a registered subject."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE subjects SET name = ?, code = ? WHERE id = ?;",
            (name.strip(), code.strip(), subject_id),
        )
        conn.commit()
        log_action("ADMIN", "UPDATE_SUBJECT", f"Updated subject ID {subject_id} to '{name}' ({code}).")
        return True


# Paper Helpers
def get_paper_by_hash(file_hash: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE file_hash = ?;", (file_hash,))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_paper(
    subject_id: int,
    year: int,
    semester: int,
    exam_type: str,
    file_hash: str,
    file_path: str,
    source_file_id: Optional[int] = None,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
    course_code: Optional[str] = None,
    course_name_raw: Optional[str] = None,
    exam_name_raw: Optional[str] = None,
    exam_date: Optional[str] = None,
    program: Optional[str] = None,
    branch: Optional[str] = None,
    study_year: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    max_marks: Optional[int] = None,
    is_makeup: int = 0,
    quality_score: Optional[float] = None,
    metadata_confidence: Optional[float] = None,
    status: str = "accepted",
) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO papers (
                subject_id, year, semester, exam_type, file_hash, file_path,
                source_file_id, page_start, page_end, course_code, course_name_raw,
                exam_name_raw, exam_date, program, branch, study_year,
                duration_minutes, max_marks, is_makeup, quality_score,
                metadata_confidence, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                subject_id,
                year,
                semester,
                exam_type.lower(),
                file_hash,
                file_path,
                source_file_id,
                page_start,
                page_end,
                course_code,
                course_name_raw,
                exam_name_raw,
                exam_date,
                program,
                branch,
                study_year,
                duration_minutes,
                max_marks,
                int(is_makeup),
                quality_score,
                metadata_confidence,
                status,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_papers_by_subject(subject_id: int) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM papers WHERE subject_id = ? ORDER BY year DESC, exam_type ASC;",
            (subject_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def update_paper_details(
    paper_id: int,
    year: int,
    semester: int,
    exam_type: str,
    course_code: Optional[str] = None,
    exam_date: Optional[str] = None,
    max_marks: Optional[int] = None,
    is_makeup: Optional[int] = None,
) -> bool:
    """Updates metadata for an ingested examination paper."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE papers 
            SET year = ?, semester = ?, exam_type = ?,
                course_code = COALESCE(?, course_code),
                exam_date = COALESCE(?, exam_date),
                max_marks = COALESCE(?, max_marks),
                is_makeup = COALESCE(?, is_makeup)
            WHERE id = ?;
            """,
            (
                int(year),
                int(semester),
                exam_type.lower().strip(),
                course_code,
                exam_date,
                max_marks,
                is_makeup,
                paper_id,
            ),
        )
        conn.commit()
        log_action("ADMIN", "UPDATE_PAPER", f"Updated paper ID {paper_id}: Year {year}, Sem {semester}, Type {exam_type}.")
        return True


def get_questions_by_paper(paper_id: int) -> List[Dict[str, Any]]:
    """Retrieves all questions extracted from a given paper."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM questions WHERE paper_id = ? ORDER BY id ASC;",
            (paper_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


# Tag Helpers
def get_all_tags(active_only: bool = True) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM tags WHERE is_active = 1 ORDER BY name ASC;")
        else:
            cursor.execute("SELECT * FROM tags ORDER BY name ASC;")
        return [dict(row) for row in cursor.fetchall()]


def add_tag(name: str, category: str = "task") -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO tags (name, category, is_active) VALUES (?, ?, 1);",
            (name.strip().lower(), category.strip().lower()),
        )
        conn.commit()
        cursor.execute("SELECT id FROM tags WHERE name = ?;", (name.strip().lower(),))
        row = cursor.fetchone()
        return row["id"] if row else 0


def toggle_tag_active(tag_id: int, is_active: bool):
    with get_db_connection() as conn:
        conn.execute("UPDATE tags SET is_active = ? WHERE id = ?;", (1 if is_active else 0, tag_id))
        conn.commit()


def merge_tags(source_tag_id: int, target_tag_id: int):
    """Merges source_tag_id into target_tag_id across all question_tags, then deactivates source_tag_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT question_id FROM question_tags WHERE tag_id = ?;", (source_tag_id,))
        q_ids = [row[0] for row in cursor.fetchall()]
        for q_id in q_ids:
            cursor.execute(
                "INSERT OR IGNORE INTO question_tags (question_id, tag_id) VALUES (?, ?);",
                (q_id, target_tag_id),
            )
        cursor.execute("DELETE FROM question_tags WHERE tag_id = ?;", (source_tag_id,))
        cursor.execute("UPDATE tags SET is_active = 0 WHERE id = ?;", (source_tag_id,))
        conn.commit()


# Question & Question Tags Helpers
def add_question(
    paper_id: int,
    question_number: str,
    question_text: str,
    content_type: str = "text",
    image_path: Optional[str] = None,
    phash: Optional[str] = None,
    diagram_group_id: Optional[int] = None,
    marks: float = 5.0,
    unit: int = 1,
    topic: str = "General",
    confidence_score: float = 1.0,
    is_reviewed: bool = False,
    tag_names: Optional[List[str]] = None,
    parent_question_number: Optional[int] = None,
    part_label: Optional[str] = None,
    co_tag: Optional[str] = None,
    page_no: Optional[int] = None,
    bbox_json: Optional[str] = None,
    is_continuation: int = 0,
    figure_path: Optional[str] = None,
    figure_phash: Optional[str] = None,
) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO questions (
                paper_id, question_number, question_text, content_type,
                image_path, phash, diagram_group_id, marks, unit, topic,
                confidence_score, is_reviewed,
                parent_question_number, part_label, co_tag, page_no,
                bbox_json, is_continuation, figure_path, figure_phash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                paper_id,
                question_number,
                question_text,
                content_type,
                image_path,
                phash,
                diagram_group_id,
                marks,
                unit,
                topic,
                confidence_score,
                1 if is_reviewed else 0,
                parent_question_number,
                part_label,
                co_tag,
                page_no,
                bbox_json,
                int(is_continuation),
                figure_path,
                figure_phash,
            ),
        )
        q_id = cursor.lastrowid

        if tag_names:
            for t_name in tag_names:
                t_name_clean = t_name.strip().lower()
                cursor.execute("SELECT id FROM tags WHERE name = ?;", (t_name_clean,))
                tag_row = cursor.fetchone()
                if not tag_row:
                    cursor.execute("INSERT INTO tags (name, category, is_active) VALUES (?, 'auto', 1);", (t_name_clean,))
                    t_id = cursor.lastrowid
                else:
                    t_id = tag_row["id"]
                cursor.execute(
                    "INSERT OR IGNORE INTO question_tags (question_id, tag_id) VALUES (?, ?);",
                    (q_id, t_id),
                )

        conn.commit()
        return q_id


def get_question_tags(question_id: int) -> List[str]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT t.name FROM tags t
            JOIN question_tags qt ON t.id = qt.tag_id
            WHERE qt.question_id = ?
            ORDER BY t.name ASC;
            """,
            (question_id,),
        )
        return [row[0] for row in cursor.fetchall()]


def update_question_tags(question_id: int, tag_names: List[str]):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM question_tags WHERE question_id = ?;", (question_id,))
        for t_name in tag_names:
            t_name_clean = t_name.strip().lower()
            cursor.execute("SELECT id FROM tags WHERE name = ?;", (t_name_clean,))
            tag_row = cursor.fetchone()
            if not tag_row:
                cursor.execute("INSERT INTO tags (name, category, is_active) VALUES (?, 'user', 1);", (t_name_clean,))
                t_id = cursor.lastrowid
            else:
                t_id = tag_row["id"]
            cursor.execute(
                "INSERT OR IGNORE INTO question_tags (question_id, tag_id) VALUES (?, ?);",
                (question_id, t_id),
            )
        conn.commit()


def get_unreviewed_questions(subject_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if subject_id:
            cursor.execute(
                """
                SELECT q.*, p.year, p.exam_type, s.name as subject_name
                FROM questions q
                JOIN papers p ON q.paper_id = p.id
                JOIN subjects s ON p.subject_id = s.id
                WHERE q.is_reviewed = 0 AND p.subject_id = ?
                ORDER BY q.confidence_score ASC, q.id DESC;
                """,
                (subject_id,),
            )
        else:
            cursor.execute(
                """
                SELECT q.*, p.year, p.exam_type, s.name as subject_name
                FROM questions q
                JOIN papers p ON q.paper_id = p.id
                JOIN subjects s ON p.subject_id = s.id
                WHERE q.is_reviewed = 0
                ORDER BY q.confidence_score ASC, q.id DESC;
                """
            )
        return [dict(row) for row in cursor.fetchall()]


def update_question_details(
    question_id: int,
    question_text: str,
    marks: float,
    unit: int,
    topic: str,
    is_reviewed: bool = True,
    question_number: Optional[str] = None,
    co_tag: Optional[str] = None,
):
    with get_db_connection() as conn:
        if question_number is not None:
            conn.execute(
                """
                UPDATE questions
                SET question_number = ?, question_text = ?, marks = ?, unit = ?, topic = ?, is_reviewed = ?,
                    co_tag = COALESCE(?, co_tag)
                WHERE id = ?;
                """,
                (question_number.strip(), question_text.strip(), marks, unit, topic.strip(), 1 if is_reviewed else 0, co_tag, question_id),
            )
        else:
            conn.execute(
                """
                UPDATE questions
                SET question_text = ?, marks = ?, unit = ?, topic = ?, is_reviewed = ?,
                    co_tag = COALESCE(?, co_tag)
                WHERE id = ?;
                """,
                (question_text.strip(), marks, unit, topic.strip(), 1 if is_reviewed else 0, co_tag, question_id),
            )
        conn.commit()


# Diagram Groups Helpers
def get_all_diagram_groups() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM diagram_groups;")
        return [dict(row) for row in cursor.fetchall()]


def add_diagram_group(group_uid: str, representative_phash: str) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO diagram_groups (group_uid, representative_phash) VALUES (?, ?);",
            (group_uid, representative_phash),
        )
        conn.commit()
        return cursor.lastrowid


# MCQ Bank Helpers
def add_mcq(
    question_id: int,
    option_a: str,
    option_b: str,
    option_c: str,
    option_d: str,
    correct_option: str,
    explanation: str,
    status: str = "draft",
) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO mcq_bank (question_id, option_a, option_b, option_c, option_d, correct_option, explanation, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                question_id,
                option_a.strip(),
                option_b.strip(),
                option_c.strip(),
                option_d.strip(),
                correct_option.strip().upper(),
                explanation.strip(),
                status.strip().lower(),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def verify_mcq(mcq_id: int) -> bool:
    """Marks an MCQ as verified by administrator."""
    with get_db_connection() as conn:
        conn.execute("UPDATE mcq_bank SET status = 'verified' WHERE id = ?;", (mcq_id,))
        conn.commit()
        log_action("ADMIN", "VERIFY_MCQ", f"Verified MCQ ID {mcq_id}.")
        return True


def get_mcq_by_question_id(question_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mcq_bank WHERE question_id = ?;", (question_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_mcqs_for_subject(subject_id: int, status: Optional[str] = "verified") -> List[Dict[str, Any]]:
    """Retrieves MCQs for a given subject, defaulting to verified items only."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute(
                """
                SELECT m.*, q.question_text, q.marks, q.unit, q.topic, q.question_number, p.year
                FROM mcq_bank m
                JOIN questions q ON m.question_id = q.id
                JOIN papers p ON q.paper_id = p.id
                WHERE p.subject_id = ? AND m.status = ?
                ORDER BY q.id ASC;
                """,
                (subject_id, status.lower()),
            )
        else:
            cursor.execute(
                """
                SELECT m.*, q.question_text, q.marks, q.unit, q.topic, q.question_number, p.year
                FROM mcq_bank m
                JOIN questions q ON m.question_id = q.id
                JOIN papers p ON q.paper_id = p.id
                WHERE p.subject_id = ?
                ORDER BY q.id ASC;
                """,
                (subject_id,),
            )
        return [dict(row) for row in cursor.fetchall()]


def get_paper_details(paper_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.*, s.name as subject_name, COUNT(q.id) as question_count
            FROM papers p
            JOIN subjects s ON p.subject_id = s.id
            LEFT JOIN questions q ON p.id = q.paper_id
            WHERE p.id = ?
            GROUP BY p.id;
            """,
            (paper_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_papers_detailed() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.*, s.name as subject_name, COUNT(q.id) as question_count
            FROM papers p
            JOIN subjects s ON p.subject_id = s.id
            LEFT JOIN questions q ON p.id = q.paper_id
            GROUP BY p.id
            ORDER BY s.name ASC, p.year DESC, p.exam_type ASC;
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_paper(paper_id: int) -> bool:
    """Removes a paper, its physical PDF, all associated cropped question images,
    and all database questions, tags, and MCQs in cascade.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Get paper file path
        cursor.execute("SELECT file_path FROM papers WHERE id = ?;", (paper_id,))
        p_row = cursor.fetchone()
        if not p_row:
            return False
        paper_file_path = p_row["file_path"]

        # 2. Get all question image paths & figure paths
        cursor.execute("SELECT image_path, figure_path FROM questions WHERE paper_id = ?;", (paper_id,))
        img_rows = cursor.fetchall()
        for img_r in img_rows:
            for path_key in ("image_path", "figure_path"):
                path_val = img_r[path_key]
                if path_val and os.path.exists(path_val):
                    try:
                        os.remove(path_val)
                    except Exception:
                        pass

        # 3. Delete physical PDF
        if paper_file_path and os.path.exists(paper_file_path):
            try:
                os.remove(paper_file_path)
            except Exception:
                pass

        # 4. Delete paper record (Cascade deletes questions, mcqs, question_tags)
        cursor.execute("DELETE FROM papers WHERE id = ?;", (paper_id,))
        conn.commit()

        log_action("ADMIN", "DELETE_PAPER", f"Deleted paper ID {paper_id} and associated question assets.")
        return True


def delete_subject(subject_id: int) -> bool:
    """Deletes an entire subject, removing all associated PDFs, question snippet images,
    and cascading database records.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM papers WHERE subject_id = ?;", (subject_id,))
        paper_ids = [row["id"] for row in cursor.fetchall()]

    for p_id in paper_ids:
        delete_paper(p_id)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subjects WHERE id = ?;", (subject_id,))
        conn.commit()
        log_action("ADMIN", "DELETE_SUBJECT", f"Deleted subject ID {subject_id} and all related papers.")
        return True


def cleanup_orphaned_records() -> Dict[str, int]:
    """Cleans up orphan MCQs and unreferenced diagram groups."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Clean orphan MCQs
        cursor.execute("DELETE FROM mcq_bank WHERE question_id NOT IN (SELECT id FROM questions);")
        cleaned_mcqs = cursor.rowcount

        # Clean unreferenced diagram groups
        cursor.execute(
            """
            DELETE FROM diagram_groups 
            WHERE id NOT IN (
                SELECT DISTINCT diagram_group_id FROM questions WHERE diagram_group_id IS NOT NULL
            );
            """
        )
        cleaned_groups = cursor.rowcount
        conn.commit()
        log_action("ADMIN", "CLEANUP_ORPHANS", f"Cleaned {cleaned_mcqs} orphaned MCQs and {cleaned_groups} unused diagram groups.")
        return {"orphaned_mcqs": cleaned_mcqs, "unused_diagram_groups": cleaned_groups}


# Database Backup & Export
def export_database_json() -> str:
    """Serializes all primary tables into a JSON string for full data backup."""
    data = {}
    tables = [
        "source_files", "subjects", "papers", "diagram_groups", "questions",
        "tags", "question_tags", "mcq_bank", "student_attempts",
        "student_responses", "audit_log"
    ]
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for t in tables:
            cursor.execute(f"SELECT * FROM {t};")
            data[t] = [dict(row) for row in cursor.fetchall()]
    return json.dumps(data, indent=2, default=str)


def backup_database_file(target_path: str) -> bool:
    """Creates a direct file copy of the SQLite database."""
    try:
        shutil.copy2(DB_PATH, target_path)
        return True
    except Exception:
        return False
