import io
import pathlib
import pyflakes.api
import pyflakes.reporter
import pytest

from modules.analytics import analyze_attempt_performance
from modules.auth import verify_dev_admin
from modules.backtester import run_historical_backtest
from modules.database import (
    add_paper,
    add_question,
    add_subject,
    create_student_account,
    delete_paper,
    get_db_connection,
    init_db,
    verify_student_account,
)
from modules.mcq_builder import TASK_VERB_MEANINGS, build_task_mcq
from modules.scoring import calculate_cluster_predictions
from modules.ui_helpers import safe


def test_pyflakes_ingestion_no_undefined_names() -> None:
    """Validates that modules/ingestion.py has no undefined names via pyflakes."""
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    reporter = pyflakes.reporter.Reporter(buf_out, buf_err)
    with open("modules/ingestion.py", "r", encoding="utf-8") as f:
        code = f.read()
    pyflakes.api.check(code, "modules/ingestion.py", reporter)
    output = buf_out.getvalue() + buf_err.getvalue()
    assert "undefined name" not in output


def test_backtest_no_leak(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Verifies that historical backtest for test_year=2024 uses strictly earlier years (2022, 2023)."""
    db_file = tmp_path / "t.db"
    monkeypatch.setattr("modules.database.DB_PATH", str(db_file))
    init_db()

    sub_id = add_subject("Algorithms", "CS301")
    p2022 = add_paper(sub_id, year=2022, semester=5, exam_type="midterm", file_hash="hash22", file_path="dummy22.pdf")
    p2023 = add_paper(sub_id, year=2023, semester=5, exam_type="midterm", file_hash="hash23", file_path="dummy23.pdf")
    p2024 = add_paper(sub_id, year=2024, semester=5, exam_type="midterm", file_hash="hash24", file_path="dummy24.pdf")

    add_question(p2022, "Q1", "Explain Dijkstra algorithm in detail.", marks=10.0, unit=1, topic="Graphs")
    add_question(p2023, "Q1", "Explain Dijkstra shortest path algorithm.", marks=10.0, unit=1, topic="Graphs")
    add_question(p2024, "Q1", "Explain Dijkstra shortest path with proof.", marks=10.0, unit=1, topic="Graphs")

    res = run_historical_backtest(sub_id, test_year=2024)
    assert res["success"] is True
    assert res["train_years"] == [2022, 2023]
    for member in res.get("matched_pairs", []):
        pred = member.get("predicted", {})
        for y in pred.get("years_appeared", []):
            assert y < 2024


def test_calculate_cluster_predictions_default_reference_year(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Verifies that default reference year when current_year=None equals max data year + 1."""
    db_file = tmp_path / "t.db"
    monkeypatch.setattr("modules.database.DB_PATH", str(db_file))
    init_db()

    sub_id = add_subject("Calculus", "MATH101")
    p2021 = add_paper(sub_id, year=2021, semester=1, exam_type="midterm", file_hash="h21", file_path="p21.pdf")
    p2023 = add_paper(sub_id, year=2023, semester=1, exam_type="midterm", file_hash="h23", file_path="p23.pdf")

    add_question(p2021, "Q1", "Evaluate double integral of x*y over unit square.", marks=5.0, unit=1, topic="Calculus")
    add_question(p2023, "Q1", "Evaluate double integral of x*y over region R.", marks=5.0, unit=1, topic="Calculus")

    preds = calculate_cluster_predictions(sub_id, current_year=None)
    assert len(preds) > 0
    # max data year is 2023, default reference year is 2024. Gap from 2023 is 2024 - 2023 = 1.
    assert preds[0]["gap_years"] == 1
    assert preds[0]["data_years"] == 2


def test_analytics_skipped_topic(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Verifies that an all-skipped topic is not in weaknesses and appears in skipped_topics."""
    db_file = tmp_path / "t.db"
    monkeypatch.setattr("modules.database.DB_PATH", str(db_file))
    init_db()

    sub_id = add_subject("Operating Systems", "CS401")
    p = add_paper(sub_id, year=2023, semester=4, exam_type="midterm", file_hash="osp", file_path="os.pdf")
    q1 = add_question(p, "Q1", "Explain deadlock prevention conditions.", marks=5.0, unit=1, topic="Deadlocks")
    q2 = add_question(p, "Q2", "Explain paging and segmentation concepts.", marks=5.0, unit=2, topic="Memory Management")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO student_attempts (student_id, subject_id, quiz_type, score, total_questions)
            VALUES (?, ?, ?, ?, ?);
            """,
            ("stu_1@student.local", sub_id, "diagnostic", 100.0, 2),
        )
        attempt_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO student_responses (attempt_id, question_id, selected_option, is_correct, is_skipped, time_taken_seconds)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (attempt_id, q1, "E", 0, 1, 15.0),
        )
        cursor.execute(
            """
            INSERT INTO student_responses (attempt_id, question_id, selected_option, is_correct, is_skipped, time_taken_seconds)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (attempt_id, q2, "A", 1, 0, 20.0),
        )
        conn.commit()

    analysis = analyze_attempt_performance(attempt_id)
    assert "Deadlocks" in analysis["skipped_topics"]
    assert "Deadlocks" not in analysis["weaknesses"]
    deadlock_summary = next(item for item in analysis["topic_summary"] if item["topic"] == "Deadlocks")
    assert deadlock_summary["accuracy"] is None
    assert deadlock_summary["all_skipped"] is True


def test_mcq_builder_distinct_options_and_varying_letters() -> None:
    """Verifies that 20 generated MCQs have 4 distinct options and vary correct option letters."""
    verbs = list(TASK_VERB_MEANINGS.keys())
    generated_mcqs = []
    for i in range(20):
        verb = verbs[i % len(verbs)]
        q_dict = {
            "id": i + 100,
            "question_text": f"Please {verb} the primary architecture and functional units of modern processors.",
        }
        mcq = build_task_mcq(q_dict)
        assert mcq is not None
        generated_mcqs.append(mcq)

    assert len(generated_mcqs) == 20
    correct_letters = set()
    for mcq in generated_mcqs:
        options = [mcq["option_a"], mcq["option_b"], mcq["option_c"], mcq["option_d"]]
        assert len(set(options)) == 4, "All 4 options must be distinct"
        assert mcq["correct_option"] in ["A", "B", "C", "D"]
        correct_letters.add(mcq["correct_option"])

    assert len(correct_letters) > 1, f"Correct options must vary across questions, got: {correct_letters}"


def test_verify_dev_admin() -> None:
    """Tests verify_dev_admin for matching, wrong, and empty passcode."""
    email = "diyanshah2301@gmail.com"
    assert verify_dev_admin(email, "admin123", "something-else") is False
    assert verify_dev_admin(email, "admin123", "admin123") is True
    assert verify_dev_admin(email, "admin123", "") is False


def test_safe_escaping() -> None:
    """Verifies that safe() escapes HTML tags like <script> properly."""
    escaped = safe("<script>x</script>")
    assert "<script>" not in escaped
    assert "&lt;script&gt;x&lt;/script&gt;" == escaped


def test_delete_paper_preserves_shared_figure(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Verifies that delete_paper does not delete a figure file referenced by another paper's question."""
    db_file = tmp_path / "t.db"
    monkeypatch.setattr("modules.database.DB_PATH", str(db_file))
    init_db()

    sub_id = add_subject("Physics", "PHY101")
    shared_fig = tmp_path / "shared_diagram.png"
    shared_fig.write_text("dummy image data", encoding="utf-8")

    p1 = add_paper(sub_id, year=2022, semester=1, exam_type="midterm", file_hash="p1_hash", file_path=str(tmp_path / "p1.pdf"))
    p2 = add_paper(sub_id, year=2023, semester=1, exam_type="midterm", file_hash="p2_hash", file_path=str(tmp_path / "p2.pdf"))

    add_question(p1, "Q1", "Analyze the circuit diagram shown in figure.", marks=5.0, figure_path=str(shared_fig))
    add_question(p2, "Q1", "Identify components from the circuit diagram.", marks=5.0, figure_path=str(shared_fig))

    assert shared_fig.exists()
    deleted = delete_paper(p1)
    assert deleted is True
    assert shared_fig.exists(), "Shared figure must be preserved when referenced by another paper"


def test_init_db_idempotence(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Verifies that init_db() can be run repeatedly without errors or data destruction."""
    db_file = tmp_path / "t.db"
    monkeypatch.setattr("modules.database.DB_PATH", str(db_file))
    init_db()

    sub_id = add_subject("Chemistry", "CHEM101")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM subjects;")
        count_before = cursor.fetchone()[0]

    # Re-run init_db()
    init_db()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM subjects;")
        count_after = cursor.fetchone()[0]

    assert count_before == count_after == 1
    assert sub_id > 0


def test_student_account_creation_and_verification(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Verifies student account creation, authentication, failure on wrong password, and PBKDF2 hashing."""
    db_file = tmp_path / "t.db"
    monkeypatch.setattr("modules.database.DB_PATH", str(db_file))
    init_db()

    created, msg = create_student_account("student123", "Alice Smith", "securepassword123")
    assert created is True
    assert "successfully" in msg.lower()

    # Verify correct password
    assert verify_student_account("student123", "securepassword123") is True

    # Verify incorrect password
    assert verify_student_account("student123", "wrongpass") is False

    # Verify non-plaintext storage
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, salt FROM student_accounts WHERE student_id = ?;", ("student123",))
        row = cursor.fetchone()
        assert row is not None
        stored_hash = row["password_hash"]
        assert stored_hash != "securepassword123"
        assert "securepassword123" not in stored_hash
        assert len(stored_hash) == 64
