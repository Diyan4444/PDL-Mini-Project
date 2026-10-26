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
    """Initializes the relational SQLite database with the full production schema."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

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

        conn.commit()


def log_action(actor: str, action: str, details: str = ""):
    """Records an audit log entry for system actions."""
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO audit_log (actor, action, details) VALUES (?, ?, ?);",
            (actor, action, details),
        )
        conn.commit()


# Subject Helpers
def get_all_subjects() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subjects ORDER BY name ASC;")
        return [dict(row) for row in cursor.fetchall()]


def add_subject(name: str, code: str = "") -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO subjects (name, code) VALUES (?, ?);",
            (name.strip(), code.strip()),
        )
        conn.commit()
        return cursor.lastrowid


# Paper Helpers
def get_paper_by_hash(file_hash: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE file_hash = ?;", (file_hash,))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_paper(subject_id: int, year: int, semester: int, exam_type: str, file_hash: str, file_path: str) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO papers (subject_id, year, semester, exam_type, file_hash, file_path)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (subject_id, year, semester, exam_type.lower(), file_hash, file_path),
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
        # Find all questions with source_tag_id
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
) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO questions (
                paper_id, question_number, question_text, content_type,
                image_path, phash, diagram_group_id, marks, unit, topic,
                confidence_score, is_reviewed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
):
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE questions
            SET question_text = ?, marks = ?, unit = ?, topic = ?, is_reviewed = ?
            WHERE id = ?;
            """,
            (question_text.strip(), marks, unit, topic.strip(), 1 if is_reviewed else 0, question_id),
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
) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO mcq_bank (question_id, option_a, option_b, option_c, option_d, correct_option, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                question_id,
                option_a.strip(),
                option_b.strip(),
                option_c.strip(),
                option_d.strip(),
                correct_option.strip().upper(),
                explanation.strip(),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_mcq_by_question_id(question_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mcq_bank WHERE question_id = ?;", (question_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# Database Backup & Export
def export_database_json() -> str:
    """Serializes all primary tables into a JSON string for full data backup."""
    data = {}
    tables = [
        "subjects", "papers", "diagram_groups", "questions",
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
