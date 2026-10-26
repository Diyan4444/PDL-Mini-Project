import os
import time
from datetime import datetime
import streamlit as st
import pandas as pd

from modules.database import (
    init_db,
    get_all_subjects,
    add_subject,
    get_all_tags,
    add_tag,
    merge_tags,
    toggle_tag_active,
    get_unreviewed_questions,
    update_question_details,
    get_question_tags,
    update_question_tags,
    export_database_json,
    log_action,
)
from modules.auth import (
    render_login_widget,
    require_admin,
    is_admin,
    get_current_user_email,
)
from modules.ingestion import process_pdf_document, download_drive_file
from modules.scoring import calculate_cluster_predictions
from modules.quiz_engine import (
    load_quiz_questions,
    init_quiz_session,
    submit_quiz_attempt,
)
from modules.analytics import analyze_attempt_performance, get_student_history
from modules.mock_generator import generate_mock_paper
from modules.backtester import run_historical_backtest
from modules.exporter import export_predictions_pdf

# 1. Page Configuration
st.set_page_config(
    page_title="Exam Predictor & Quiz System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database schema on startup
init_db()

# 2. Inject Custom CSS for Glowing Green/Black Toggle Tags and Badges
CUSTOM_CSS = """
<style>
/* Glowing Green Active Tag Buttons */
div.stButton > button.tag-btn-active {
    background-color: #28a745 !important;
    color: #000000 !important;
    font-weight: 700 !important;
    border: 2px solid #1e7e34 !important;
    box-shadow: 0 0 12px rgba(40, 167, 69, 0.8) !important;
    border-radius: 20px !important;
    transition: all 0.2s ease-in-out !important;
}

div.stButton > button.tag-btn-inactive {
    background-color: #f8f9fa !important;
    color: #495057 !important;
    font-weight: 500 !important;
    border: 1px solid #ced4da !important;
    border-radius: 20px !important;
}

div.stButton > button.tag-btn-inactive:hover {
    border-color: #28a745 !important;
    color: #28a745 !important;
}

/* Card Styling */
.metric-card {
    background: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 10px;
    padding: 16px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
}

.disclaimer-banner {
    background-color: #fff3cd;
    color: #856404;
    padding: 10px 16px;
    border-radius: 6px;
    border-left: 5px solid #ffeeba;
    font-size: 0.88rem;
    margin-bottom: 20px;
}

.badge-high {
    background-color: #d4edda;
    color: #155724;
    padding: 4px 10px;
    border-radius: 12px;
    font-weight: bold;
    font-size: 0.85rem;
}
.badge-med {
    background-color: #fff3cd;
    color: #856404;
    padding: 4px 10px;
    border-radius: 12px;
    font-weight: bold;
    font-size: 0.85rem;
}
.badge-low {
    background-color: #e2e3e5;
    color: #383d41;
    padding: 4px 10px;
    border-radius: 12px;
    font-weight: bold;
    font-size: 0.85rem;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_disclaimer():
    """Renders prominent disclaimer on all views."""
    st.markdown(
        """
        <div class="disclaimer-banner">
            ⚠️ <b>Academic Disclaimer:</b> Predictions are calculated purely using deterministic historical recurrence heuristics 
            (frequency, recency decay, cycle gaps, and syllabus marks). They do not represent a guaranteed or leaked examination paper.
        </div>
        """,
        unsafe_allow_html=True,
    )


# 3. Sidebar Navigation & Session
render_login_widget()

with st.sidebar:
    st.markdown("---")
    st.markdown("### 📌 Navigation")
    current_email = get_current_user_email()
    has_admin_priv = is_admin(current_email)

    menu_options = [
        "📊 Predictions & Likelihood",
        "📝 Practice Quiz & MCQ Bank",
        "📈 Diagnostic Report & Progress",
        "📑 Mock Exam Generator",
        "🔬 Back-Testing Lab Engine",
    ]
    if has_admin_priv:
        menu_options.append("🛡️ Admin Management Portal")

    # Keep track of active navigation
    default_idx = 0
    if "nav_selection" in st.session_state and st.session_state.nav_selection in menu_options:
        default_idx = menu_options.index(st.session_state.nav_selection)

    selected_page = st.radio("Select View", menu_options, index=default_idx)
    st.session_state.nav_selection = selected_page

# ==============================================================================
# VIEW 1: PREDICTIONS & LIKELIHOOD DASHBOARD
# ==============================================================================
if selected_page == "📊 Predictions & Likelihood":
    st.title("📊 Question Repetition & Exam Likelihood Engine")
    render_disclaimer()

    subjects = get_all_subjects()
    if not subjects:
        st.info("No subjects or question papers have been ingested yet. Please contact the administrator or add papers via the Admin Portal.")
        st.stop()

    subj_map = {s["name"]: s["id"] for s in subjects}
    
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 1, 1])
    with col_ctrl1:
        chosen_subj_name = st.selectbox("Select Subject", list(subj_map.keys()))
        chosen_subj_id = subj_map.get(chosen_subj_name)
        if not chosen_subj_id:
            st.stop()
    with col_ctrl2:
        exam_filter = st.selectbox("Exam Type", ["All", "Midterm", "Endterm"])
    with col_ctrl3:
        target_unit_options = st.multiselect("Filter Units", [1, 2, 3, 4, 5], default=[1, 2, 3, 4, 5])

    exam_filter_param = None if exam_filter == "All" else exam_filter.lower()
    predictions = calculate_cluster_predictions(chosen_subj_id, exam_type=exam_filter_param)

    if target_unit_options:
        predictions = [p for p in predictions if p["unit"] in target_unit_options]

    if not predictions:
        st.warning("No questions match the current filters. Ingest additional past papers to view predictions.")
        st.stop()

    # Metric summaries
    high_count = sum(1 for p in predictions if p["likelihood"] == "High")
    med_count = sum(1 for p in predictions if p["likelihood"] == "Medium")
    low_count = sum(1 for p in predictions if p["likelihood"] == "Low")

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Total Analyzed Clusters", len(predictions))
    col_m2.metric("High Likelihood (>=70%)", high_count)
    col_m3.metric("Medium Likelihood (45-69%)", med_count)
    col_m4.metric("Low Likelihood (<45%)", low_count)

    st.markdown("---")
    
    col_act1, col_act2 = st.columns([3, 1])
    with col_act1:
        search_query = st.text_input("🔍 Search predicted questions by keyword", "")
    with col_act2:
        if st.button("📥 Export Study Sheet (PDF)", use_container_width=True):
            pdf_path = export_predictions_pdf(chosen_subj_name, predictions)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download PDF",
                    data=f.read(),
                    file_name=f"{chosen_subj_name}_predictions.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

    filtered_preds = [
        p for p in predictions if search_query.lower() in p["question_text"].lower()
    ] if search_query else predictions

    # Display Predictions
    for p in filtered_preds:
        badge_cls = "badge-high" if p["likelihood"] == "High" else ("badge-med" if p["likelihood"] == "Medium" else "badge-low")
        years_str = ", ".join(map(str, p["years_appeared"]))

        with st.container():
            st.markdown(
                f"""
                <div style="background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 8px; padding: 14px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-weight: 600; font-size: 1.05rem;">Unit {p['unit']} | {p['topic']} ({p['avg_marks']} Marks)</span>
                        <span class="{badge_cls}">{p['likelihood']} Likelihood ({p['final_score']}%)</span>
                    </div>
                    <p style="font-size: 1rem; color: #212529; margin-bottom: 8px;">{p['question_text']}</p>
                    <div style="font-size: 0.85rem; color: #6c757d;">
                        🗓️ <b>Appeared in:</b> {years_str} (Total: {p['appearances_count']} times) | 
                        ⏳ <b>Gap:</b> {p['gap_years']} yrs | 
                        📊 <b>Freq Score:</b> {p['frequency_score']}% | <b>Recency:</b> {p['recency_score']}%
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if p["image_path"] and os.path.exists(p["image_path"]):
                st.image(p["image_path"], caption=f"Extracted Figure (Cluster #{p['cluster_id']})", width=260)


# ==============================================================================
# VIEW 2: PRACTICE QUIZ & MCQ BANK
# ==============================================================================
elif selected_page == "📝 Practice Quiz & MCQ Bank":
    st.title("📝 Adaptive Practice Quiz & MCQ Bank")
    render_disclaimer()

    subjects = get_all_subjects()
    if not subjects:
        st.info("No question papers available.")
        st.stop()

    subj_map = {s["name"]: s["id"] for s in subjects}

    # If quiz is not running, show setup
    if not st.session_state.get("quiz_questions") or st.session_state.get("quiz_completed", False):
        st.subheader("Quiz Setup")
        c1, c2, c3 = st.columns(3)
        with c1:
            q_subj_name = st.selectbox("Subject", list(subj_map.keys()), key="quiz_subj_select")
            q_subj_id = subj_map.get(q_subj_name)
        with c2:
            q_exam_type = st.selectbox("Target Exam", ["All", "Midterm", "Endterm"], key="quiz_exam_select")
        with c3:
            q_num_items = st.slider("Number of Questions", min_value=3, max_value=25, value=5)

        c4, c5 = st.columns(2)
        with c4:
            q_units = st.multiselect("Units Covered", [1, 2, 3, 4, 5], default=[1, 2, 3], key="quiz_units_select")
        with c5:
            q_text_only = st.checkbox("Text-only Questions (exclude diagrams)", value=False)

        if st.button("🚀 Start Quiz", type="primary", use_container_width=True):
            if not q_subj_id:
                st.error("Please select a valid subject.")
                st.stop()
            items = load_quiz_questions(
                subject_id=q_subj_id,
                exam_type=None if q_exam_type == "All" else q_exam_type,
                units=q_units,
                text_only=q_text_only,
                limit=q_num_items,
            )
            if not items:
                st.error("No questions found matching your filter criteria. Please widen your syllabus unit selection.")
            else:
                init_quiz_session(items)
                st.session_state.active_quiz_subject_id = q_subj_id
                st.rerun()

    else:
        # Running Quiz Session
        questions = st.session_state.quiz_questions
        idx = st.session_state.quiz_current_index
        total = len(questions)
        q = questions[idx]

        st.progress((idx + 1) / total, text=f"Question {idx + 1} of {total}")

        st.markdown(
            f"""
            <div style="background-color: #f8f9fa; border-left: 5px solid #28a745; padding: 14px; border-radius: 4px; margin-bottom: 15px;">
                <span style="font-size: 0.9rem; color: #6c757d;">Unit {q['unit']} | {q['topic']} | Marks: {q['marks']}</span>
                <h4 style="margin-top: 5px;">{q['question_text']}</h4>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if q["image_path"] and os.path.exists(q["image_path"]):
            st.image(q["image_path"], caption="Question Diagram / Formula", width=320)

        # 5 Options including "Not in my syllabus / Skip"
        option_choices = [
            f"A) {q['options']['A']}",
            f"B) {q['options']['B']}",
            f"C) {q['options']['C']}",
            f"D) {q['options']['D']}",
            f"E) {q['options']['E']}",
        ]

        # Check existing answer
        saved_resp = st.session_state.quiz_responses.get(idx, {}).get("selected_option")
        default_index = None
        if saved_resp:
            letter_map = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
            default_index = letter_map.get(saved_resp)

        selected_radio = st.radio(
            "Select Answer:",
            option_choices,
            index=default_index,
            key=f"q_radio_{idx}",
        )

        col_nav1, col_nav2 = st.columns([1, 1])
        with col_nav1:
            if idx > 0:
                if st.button("⬅️ Previous Question", use_container_width=True):
                    st.session_state.quiz_current_index -= 1
                    st.rerun()

        with col_nav2:
            button_label = "Finish & Submit Quiz" if (idx == total - 1) else "Next Question ➡️"
            if st.button(button_label, type="primary", use_container_width=True):
                if selected_radio:
                    chosen_letter = selected_radio[0]
                    elapsed = time.time() - st.session_state.quiz_q_start_time
                    st.session_state.quiz_responses[idx] = {
                        "selected_option": chosen_letter,
                        "duration": round(elapsed, 1),
                    }

                if idx == total - 1:
                    student_id = get_current_user_email() or "guest_student"
                    subj_id = st.session_state.get("active_quiz_subject_id", 1)
                    attempt_id = submit_quiz_attempt(student_id, subj_id)
                    st.session_state.last_attempt_id = attempt_id
                    st.session_state.quiz_completed = True
                    st.rerun()
                else:
                    st.session_state.quiz_current_index += 1
                    st.session_state.quiz_q_start_time = time.time()
                    st.rerun()


# ==============================================================================
# VIEW 3: DIAGNOSTIC REPORT & PROGRESS
# ==============================================================================
elif selected_page == "📈 Diagnostic Report & Progress":
    st.title("📈 Student Diagnostic Report & Weakness Matrix")
    render_disclaimer()

    last_attempt_id = st.session_state.get("last_attempt_id")
    student_id = get_current_user_email() or "guest_student"

    if not last_attempt_id:
        history = get_student_history(student_id)
        if history:
            last_attempt_id = history[0]["id"]
        else:
            st.info("No completed quiz attempts found. Please complete a practice quiz first.")
            st.stop()

    report = analyze_attempt_performance(last_attempt_id)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Overall Score", f"{report['score_percent']}%")
    col2.metric("Correct Answers", report["correct_count"])
    col3.metric("Mistakes", report["wrong_count"])
    col4.metric("Skipped (Out of Syllabus)", report["skipped_count"])

    st.markdown("---")
    
    # Strengths and Weaknesses
    c_str, c_wk = st.columns(2)
    with c_str:
        st.success("🌟 **Strong Knowledge Areas:**")
        if report["strengths"]:
            for s in report["strengths"]:
                st.markdown(f"- ✅ **{s}**")
        else:
            st.write("Complete more questions to establish strong topics.")

    with c_wk:
        st.error("⚠️ **High Priority Revision Areas:**")
        if report["weaknesses"]:
            for w in report["weaknesses"]:
                st.markdown(f"- 🚩 **{w}**")
        else:
            st.write("No major weak spots detected!")

    st.markdown("### 🎯 Revision Priority Matrix (Weakness × Exam Likelihood)")
    st.write("This matrix weights the concepts you missed by how likely they are to appear on the exam:")

    df_topics = pd.DataFrame(report["topic_summary"])
    if not df_topics.empty:
        st.dataframe(
            df_topics[[
                "topic", "unit", "total_attempted", "correct",
                "accuracy", "avg_likelihood", "priority_score", "recommended_book"
            ]],
            use_container_width=True,
        )

    # Mistakes Review
    if report["mistakes"]:
        st.markdown("### 🔍 Mistakes Breakdown & Recommended Correction")
        for m in report["mistakes"]:
            with st.expander(f"❌ Question {m['question_number']} ({m['topic']})"):
                st.write(f"**Question:** {m['question_text']}")
                st.write(f"**Your Answer:** Option {m['selected_option']}")
                st.write(f"**Correct Answer:** Option {m['correct_option']}")
                st.info(f"💡 **Explanation & Book Pointer:** {m['explanation']}")

    # 1-Click Remedial Quiz
    if report["mistakes"]:
        st.markdown("---")
        if st.button("🔁 Launch 1-Click Remedial Quiz (Retry Failed Questions Only)", type="primary"):
            failed_q_ids = [m["question_id"] for m in report["mistakes"]]
            with get_db_connection() as conn:
                cursor = conn.cursor()
                placeholders = ",".join(["?"] * len(failed_q_ids))
                cursor.execute(f"SELECT * FROM questions WHERE id IN ({placeholders});", tuple(failed_q_ids))
                rem_questions = [dict(r) for r in cursor.fetchall()]

            formatted = []
            for r in rem_questions:
                formatted.append({
                    "question_id": r["id"],
                    "question_number": r["question_number"],
                    "question_text": r["question_text"],
                    "content_type": r["content_type"],
                    "image_path": r["image_path"],
                    "marks": r["marks"],
                    "unit": r["unit"],
                    "topic": r["topic"],
                    "options": {
                        "A": "Primary analytical rule",
                        "B": "Secondary implementation rule",
                        "C": "Neither condition",
                        "D": "Both conditions apply",
                        "E": "🚫 Not in my syllabus / Skip",
                    },
                    "correct_option": "A",
                    "explanation": f"Reviewing mistake for question {r['question_number']}.",
                })

            init_quiz_session(formatted)
            st.session_state.selected_page = "📝 Practice Quiz & MCQ Bank"
            st.rerun()


# ==============================================================================
# VIEW 4: MOCK EXAM GENERATOR
# ==============================================================================
elif selected_page == "📑 Mock Exam Generator":
    st.title("📑 Blueprint-Compliant Mock Exam Paper Generator")
    render_disclaimer()

    subjects = get_all_subjects()
    if not subjects:
        st.info("No subjects available.")
        st.stop()

    subj_map = {s["name"]: s["id"] for s in subjects}

    c1, c2 = st.columns(2)
    with c1:
        mock_subj_name = st.selectbox("Subject", list(subj_map.keys()))
        mock_subj_id = subj_map.get(mock_subj_name)
    with c2:
        mock_type = st.selectbox("Exam Blueprint Pattern", ["Midterm (40 Marks)", "Endterm (100 Marks)"])

    exam_type_clean = "midterm" if "Midterm" in (mock_type or "") else "endterm"
    target_marks = 40 if exam_type_clean == "midterm" else 100

    if st.button("🎲 Assemble Official Mock Paper", type="primary", use_container_width=True):
        if not mock_subj_id:
            st.error("Please select a subject.")
            st.stop()
        paper = generate_mock_paper(mock_subj_id, exam_type=exam_type_clean, target_marks=target_marks)
        st.session_state.current_mock_paper = paper

    if "current_mock_paper" in st.session_state:
        paper = st.session_state.current_mock_paper
        st.markdown("---")
        
        # Examination Header
        st.markdown(
            f"""
            <div style="text-align: center; border: 2px solid #333; padding: 20px; border-radius: 6px; background-color: #fafafa; margin-bottom: 25px;">
                <h2 style="margin: 0;">DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING</h2>
                <h4 style="margin: 5px 0;">{paper['exam_type']} EXAMINATION - SIMULATED PATTERN</h4>
                <p><b>Subject:</b> {paper['subject_name']} ({paper['subject_code']}) | <b>Max Marks:</b> {paper['total_marks']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for sec in paper["sections"]:
            st.markdown(f"### {sec['section_name']}")
            st.markdown(f"*{sec['instructions']}*")
            for q in sec["questions"]:
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px dotted #ccc; padding: 8px 0;">
                        <div>
                            <b>{q['q_num']}.</b> {q['text']} 
                            <span style="font-size: 0.8rem; color: #6c757d;">(Unit {q['unit']} | Likelihood: {q['likelihood']})</span>
                        </div>
                        <div style="font-weight: bold; min-width: 60px; text-align: right;">[{int(q['marks'])} M]</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if q["image_path"] and os.path.exists(q["image_path"]):
                    st.image(q["image_path"], width=250)


# ==============================================================================
# VIEW 5: BACK-TESTING LAB ENGINE
# ==============================================================================
elif selected_page == "🔬 Back-Testing Lab Engine":
    st.title("🔬 Historical Back-Testing & Accuracy Validation")
    render_disclaimer()

    st.write(
        """
        **Scientific Validation for Lab Presentation:**
        This module hides an actual past exam year (Year $T$), trains the heuristic scoring engine 
        strictly on prior years ($T-5$ to $T-1$), and objectively measures the hit-rate of predicted questions 
        against the questions that actually appeared on that year's paper.
        """
    )

    subjects = get_all_subjects()
    if not subjects:
        st.info("No subjects available.")
        st.stop()

    subj_map = {s["name"]: s["id"] for s in subjects}

    col1, col2 = st.columns(2)
    with col1:
        bt_subj_name = st.selectbox("Select Subject", list(subj_map.keys()))
        bt_subj_id = subj_map.get(bt_subj_name)
    with col2:
        test_year = st.number_input("Test Year to Simulate (Target Year)", min_value=2018, max_value=2026, value=2024)

    if st.button("🚀 Execute Back-Test Simulation", type="primary", use_container_width=True):
        if not bt_subj_id:
            st.error("Please select a subject.")
            st.stop()
        with st.spinner("Simulating past paper predictions..."):
            results = run_historical_backtest(bt_subj_id, int(test_year))

        if not results["success"]:
            st.error(results["message"])
        else:
            col_res1, col_res2, col_res3 = st.columns(3)
            col_res1.metric("Empirical Hit-Rate", f"{results['hit_rate']}%")
            col_res2.metric("Total Actual Questions in Paper", results["total_actual"])
            col_res3.metric("Verified Prediction Hits", results["hits_count"])

            st.markdown("### 🎯 Verified Match Breakdown")
            if results["matched_pairs"]:
                df_hits = pd.DataFrame(results["matched_pairs"])
                st.dataframe(
                    df_hits[["actual_question", "predicted_question", "similarity", "predicted_score", "marks"]],
                    use_container_width=True,
                )
            else:
                st.info("No questions from the top percentile matched this year's paper.")


# ==============================================================================
# VIEW 6: ADMIN MANAGEMENT PORTAL (RESTRICTED)
# ==============================================================================
elif selected_page == "🛡️ Admin Management Portal":
    if not require_admin():
        st.stop()

    st.title("🛡️ Administrator Management Portal")
    render_disclaimer()

    tab_ingest, tab_review, tab_tags, tab_db = st.tabs([
        "📥 Ingest Question Papers",
        "🔍 Low-Confidence Review Queue",
        "🏷️ Tag & Syllabus Manager",
        "💾 System Maintenance & DB",
    ])

    # SUB-TAB 1: INGESTION PIPELINE
    with tab_ingest:
        st.subheader("Ingest Question Paper (PDF)")

        subjects = get_all_subjects()
        subject_names = [s["name"] for s in subjects]
        
        with st.expander("➕ Register New Subject / Branch", expanded=False):
            new_s_name = st.text_input("Subject Name (e.g. Compiler Design)")
            new_s_code = st.text_input("Subject Code (e.g. CS601)")
            if st.button("Add Subject", key="btn_add_subj"):
                if new_s_name.strip():
                    add_subject(new_s_name.strip(), new_s_code.strip())
                    st.success(f"Added subject '{new_s_name}'.")
                    st.rerun()

        if not subjects:
            st.warning("Please add at least one subject above before uploading papers.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                sel_subj_name = st.selectbox("Subject", subject_names, key="ingest_subj")
                sel_subj_id = next(s["id"] for s in subjects if s["name"] == sel_subj_name)
            with c2:
                in_year = st.number_input("Year of Exam", min_value=2015, max_value=2030, value=2024)
            with c3:
                in_sem = st.number_input("Semester", min_value=1, max_value=8, value=6)
            with c4:
                in_type = st.selectbox("Exam Type", ["midterm", "endterm"])

            intake_mode = st.radio("Intake Method", ["Local PDF Upload", "Public Google Drive Link"])

            pdf_bytes = None
            orig_filename = ""

            if intake_mode == "Local PDF Upload":
                uploaded_file = st.file_uploader("Upload Question Paper PDF", type=["pdf"])
                if uploaded_file:
                    pdf_bytes = uploaded_file.read()
                    orig_filename = uploaded_file.name
            else:
                drive_url = st.text_input("Public Google Drive Link (with view permission)")
                if st.button("Fetch from Drive"):
                    if drive_url:
                        with st.spinner("Downloading from Drive via gdown..."):
                            temp_dl = os.path.join("data", "temp_drive_paper.pdf")
                            ok = download_drive_file(drive_url, temp_dl)
                            if ok:
                                with open(temp_dl, "rb") as f:
                                    pdf_bytes = f.read()
                                orig_filename = "drive_downloaded_paper.pdf"
                                st.success("Document downloaded from Google Drive.")
                            else:
                                st.error("Failed to download from Drive. Verify that link is public.")

            if pdf_bytes and st.button("⚡ Run Extraction & Ingestion Pipeline", type="primary"):
                with st.spinner("Executing extraction, OCR check, diagram clustering, and heuristic scoring..."):
                    actor = get_current_user_email() or "diyanshah2301@gmail.com"
                    success, msg, summary = process_pdf_document(
                        file_bytes=pdf_bytes,
                        original_filename=orig_filename,
                        subject_id=sel_subj_id,
                        year=int(in_year),
                        semester=int(in_sem),
                        exam_type=in_type,
                        actor_email=actor,
                    )
                if success:
                    st.success(msg)
                    st.json(summary)
                else:
                    st.error(msg)

    # SUB-TAB 2: REVIEW QUEUE
    with tab_review:
        st.subheader("🔍 Low-Confidence Extraction Review Queue")
        st.write("Questions with confidence scores < 80% or unparsed marks are routed here for verification:")

        unreviewed = get_unreviewed_questions()
        if not unreviewed:
            st.success("✅ All extracted questions have been verified and approved!")
        else:
            st.info(f"{len(unreviewed)} questions currently awaiting admin review.")
            all_db_tags = [t["name"] for t in get_all_tags(active_only=True)]

            for q in unreviewed[:10]:
                q_id = q["id"]
                st.markdown(f"#### Question #{q['question_number']} | Paper ID: {q['paper_id']} ({q['year']} {q['exam_type'].upper()})")
                
                col_ed1, col_ed2 = st.columns([2, 1])
                with col_ed1:
                    new_text = st.text_area("Question Text", q["question_text"], key=f"rev_text_{q_id}", height=120)
                    if q["image_path"] and os.path.exists(q["image_path"]):
                        st.image(q["image_path"], caption="Extracted Diagram", width=220)

                with col_ed2:
                    new_marks = st.number_input("Marks", value=float(q["marks"]), min_value=1.0, max_value=30.0, step=0.5, key=f"rev_m_{q_id}")
                    new_unit = st.number_input("Unit", value=int(q["unit"]), min_value=1, max_value=10, key=f"rev_u_{q_id}")
                    new_topic = st.text_input("Topic Name", value=q["topic"], key=f"rev_top_{q_id}")

                # INTERACTIVE GLOWING TOGGLE TAGS
                st.markdown("##### 🏷️ Assign / Toggle Tags (Multi-select with Green Glow):")
                current_assigned_tags = get_question_tags(q_id)
                session_tag_key = f"active_tags_q_{q_id}"
                if session_tag_key not in st.session_state:
                    st.session_state[session_tag_key] = set(current_assigned_tags)

                # Render tag buttons horizontally
                tag_cols = st.columns(6)
                for t_idx, tag_name in enumerate(all_db_tags):
                    col_target = tag_cols[t_idx % 6]
                    is_active = tag_name in st.session_state[session_tag_key]
                    btn_label = f"✓ {tag_name}" if is_active else tag_name
                    
                    with col_target:
                        if st.button(
                            btn_label,
                            key=f"tag_toggle_{q_id}_{tag_name}",
                            help=f"Click to toggle '{tag_name}' tag",
                            use_container_width=True,
                        ):
                            if is_active:
                                st.session_state[session_tag_key].remove(tag_name)
                            else:
                                st.session_state[session_tag_key].add(tag_name)
                            st.rerun()

                # Action Button to Commit Review
                if st.button(f"💾 Save & Approve Question #{q['question_number']}", key=f"btn_save_q_{q_id}", type="primary"):
                    final_tags = list(st.session_state[session_tag_key])
                    update_question_details(
                        question_id=q_id,
                        question_text=new_text,
                        marks=new_marks,
                        unit=new_unit,
                        topic=new_topic,
                        is_reviewed=True,
                    )
                    update_question_tags(q_id, final_tags)
                    log_action(
                        actor=get_current_user_email(),
                        action="APPROVE_QUESTION",
                        details=f"Question ID {q_id} approved with tags {final_tags}.",
                    )
                    st.success(f"Question #{q['question_number']} approved.")
                    st.rerun()

                st.markdown("---")

    # SUB-TAB 3: TAG & SYLLABUS MANAGER
    with tab_tags:
        st.subheader("🏷️ Tag Palette & Vocabulary Manager")

        c_t1, c_t2 = st.columns(2)
        with c_t1:
            st.markdown("##### Add New Vocabulary Tag")
            new_tag_name = st.text_input("Tag Name (e.g., 'waveforms', 'timing-analysis')")
            new_tag_cat = st.selectbox("Category", ["task", "content", "topic", "custom"])
            if st.button("➕ Add Tag"):
                if new_tag_name.strip():
                    add_tag(new_tag_name.strip(), new_tag_cat)
                    st.success(f"Tag '{new_tag_name}' created.")
                    st.rerun()

        with c_t2:
            st.markdown("##### Merge Two Tags")
            all_tags = get_all_tags(active_only=False)
            tag_names_all = [t["name"] for t in all_tags]
            src_tag = st.selectbox("Source Tag (To be merged and deactivated)", tag_names_all, key="src_tag")
            tgt_tag = st.selectbox("Target Tag (Consolidated)", [t for t in tag_names_all if t != src_tag], key="tgt_tag")
            if st.button("🔀 Execute Merge"):
                s_id = next(t["id"] for t in all_tags if t["name"] == src_tag)
                t_id = next(t["id"] for t in all_tags if t["name"] == tgt_tag)
                merge_tags(s_id, t_id)
                st.success(f"Merged '{src_tag}' into '{tgt_tag}'.")
                st.rerun()

        st.markdown("##### Existing Tag Inventory")
        active_tags_list = get_all_tags(active_only=False)
        st.dataframe(pd.DataFrame(active_tags_list), use_container_width=True)

    # SUB-TAB 4: DB MAINTENANCE & RECOMPUTE
    with tab_db:
        st.subheader("💾 Database Maintenance & Predictions Recomputation")
        
        st.write(
            """
            When new question papers are uploaded 2 or 3 years into the future, 
            click **Recompute All Predictions** below. The system recalculates all recurrence weights,
            updates recency exponential decays, and integrates newly joined diagram groups without altering existing tags.
            """
        )

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("🔄 Recompute All Predictions Across Subjects", type="primary", use_container_width=True):
                all_subs = get_all_subjects()
                for s in all_subs:
                    calculate_cluster_predictions(s["id"])
                st.success("All predictions successfully recomputed with updated recency and gap scores.")

        with col_b2:
            db_json = export_database_json()
            st.download_button(
                label="📦 Download Complete Database JSON Backup",
                data=db_json,
                file_name=f"exam_predictor_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
            )
