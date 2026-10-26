import json
import os
import time
from datetime import datetime
import cv2
import numpy as np
import pandas as pd
import pymupdf
import streamlit as st

from modules.database import (
    get_db_connection,
    init_db,
    get_all_subjects,
    add_subject,
    update_subject,
    delete_subject,
    delete_paper,
    update_paper_details,
    get_all_papers_detailed,
    get_questions_by_paper,
    get_all_tags,
    add_tag,
    merge_tags,
    get_questions_for_review,
    approve_all_high_confidence_questions,
    update_question_details,
    get_question_tags,
    update_question_tags,
    export_database_json,
    log_action,
    add_mcq,
    verify_mcq,
    get_mcqs_for_subject,
    preview_orphans,
    cleanup_orphans,
)
from modules.auth import (
    render_login_widget,
    require_admin,
    is_admin,
    get_current_user_email,
)
from modules.ingestion import process_pdf_document, download_drive_file, ingest_combined_pdf
from modules.scoring import calculate_cluster_predictions
from modules.quiz_engine import (
    load_quiz_questions,
    load_questions_by_ids,
    init_quiz_session,
    submit_quiz_attempt,
)
from modules.analytics import analyze_attempt_performance, get_student_history
from modules.mock_generator import generate_mock_paper
from modules.backtester import run_historical_backtest, run_rolling_backtest
from modules.exporter import export_predictions_pdf
from modules.dashboard import get_overview_stats
from modules.mcq_builder import generate_mcqs_for_subject
from modules.preprocess import preprocess_page_image
from modules.ui_helpers import safe, empty_state

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
/* Glowing Green Active Tag Buttons with st-key selectors */
div[class*="st-key-tag_act_"] button,
div[class*="st-key-btn_tag_active"] button,
div.stButton > button.tag-btn-active {
    background-color: #28a745 !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    border: 2px solid #1e7e34 !important;
    box-shadow: 0 0 12px rgba(40, 167, 69, 0.8) !important;
    border-radius: 20px !important;
    transition: all 0.2s ease-in-out !important;
}

div[class*="st-key-tag_inact_"] button,
div[class*="st-key-btn_tag_inactive"] button,
div.stButton > button.tag-btn-inactive {
    background-color: rgba(128, 128, 128, 0.10) !important;
    color: inherit !important;
    font-weight: 500 !important;
    border: 1px solid rgba(128, 128, 128, 0.35) !important;
    border-radius: 20px !important;
}

div[class*="st-key-tag_inact_"] button:hover,
div.stButton > button.tag-btn-inactive:hover {
    border-color: #28a745 !important;
    color: #28a745 !important;
}

/* Card Styling */
.metric-card {
    background: rgba(128, 128, 128, 0.10);
    border: 1px solid rgba(128, 128, 128, 0.35);
    border-radius: 10px;
    padding: 16px;
    color: inherit;
}

.disclaimer-banner {
    background-color: rgba(255, 193, 7, 0.15);
    color: inherit;
    padding: 10px 16px;
    border-radius: 6px;
    border-left: 5px solid #ffc107;
    font-size: 0.88rem;
    margin-bottom: 20px;
}

.badge-high {
    background-color: rgba(40, 167, 69, 0.20);
    color: #28a745;
    padding: 4px 10px;
    border-radius: 12px;
    font-weight: bold;
    font-size: 0.85rem;
}
.badge-med {
    background-color: rgba(255, 193, 7, 0.20);
    color: #ffc107;
    padding: 4px 10px;
    border-radius: 12px;
    font-weight: bold;
    font-size: 0.85rem;
}
.badge-low {
    background-color: rgba(128, 128, 128, 0.20);
    color: inherit;
    opacity: 0.8;
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
        "🏠 Overview Dashboard",
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
# VIEW 0: OVERVIEW DASHBOARD
# ==============================================================================
if selected_page == "🏠 Overview Dashboard":
    st.title("🏠 Examination Analytics & Overview Dashboard")
    render_disclaimer()

    subjects = get_all_subjects()
    if not subjects:
        empty_state("No examination papers or subjects have been ingested yet. Please use the Admin Portal to upload papers.")
        st.stop()

    subj_options = {"All Subjects": None}
    for s in subjects:
        subj_options[f"{s['name']} ({s.get('code') or 'General'})"] = s["id"]

    sel_sub_label = st.selectbox("Scope Dashboard", list(subj_options.keys()))
    sel_sub_id = subj_options[sel_sub_label]

    stats = get_overview_stats(sel_sub_id)

    # 4 Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Papers Loaded", stats["papers_count"])
    c2.metric("Questions Extracted", stats["questions_count"])
    c3.metric("Years Covered", stats["distinct_years_count"])
    c4.metric("Verified MCQs", stats["mcqs_verified"])

    st.markdown("---")
    ch_col1, ch_col2 = st.columns(2)
    with ch_col1:
        st.subheader("📊 Average Question Likelihood per Unit")
        if stats["unit_avg_likelihood"]:
            df_lik = pd.DataFrame(
                list(stats["unit_avg_likelihood"].items()),
                columns=["Unit", "Average Likelihood (%)"],
            ).set_index("Unit")
            st.bar_chart(df_lik)
        else:
            st.info("No likelihood predictions computed yet.")

    with ch_col2:
        st.subheader("📚 Questions per Syllabus Unit")
        if stats["questions_per_unit"]:
            df_q = pd.DataFrame(
                list(stats["questions_per_unit"].items()),
                columns=["Unit", "Question Count"],
            ).set_index("Unit")
            st.bar_chart(df_q)
        else:
            st.info("No unit question counts available.")

    st.markdown("---")
    st.subheader("🔥 Top 5 High-Likelihood Exam Questions")
    if stats["top_predictions"]:
        for p in stats["top_predictions"]:
            badge_cls = "badge-high" if p["likelihood"] == "High" else ("badge-med" if p["likelihood"] == "Medium" else "badge-low")
            years_str = safe(", ".join(map(str, p["years_appeared"])))
            st.markdown(
                f"""
                <div style="background-color: rgba(128,128,128,0.10); border: 1px solid rgba(128,128,128,0.35); border-radius: 8px; padding: 14px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-weight: 600; font-size: 1.05rem;">Unit {p['unit']} | {safe(p['topic'])} ({p['avg_marks']} Marks)</span>
                        <span class="{badge_cls}">{safe(p['likelihood'])} ({p['final_score']}%)</span>
                    </div>
                    <p style="font-size: 1rem; color: inherit; margin-bottom: 8px;">{safe(p['question_text'])}</p>
                    <div style="font-size: 0.85rem; opacity: 0.7;">
                        🗓️ <b>Appeared in:</b> {years_str} (Total: {p['appearances_count']} times) | 
                        ⏳ <b>Gap:</b> {p['gap_years']} yrs | 
                        📊 <b>Freq:</b> {p['frequency_score']}% | <b>Recency:</b> {p['recency_score']}%
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        empty_state("No predicted questions available for display.")


# ==============================================================================
# VIEW 1: PREDICTIONS & LIKELIHOOD DASHBOARD
# ==============================================================================
elif selected_page == "📊 Predictions & Likelihood":
    st.title("📊 Question Repetition & Exam Likelihood Engine")
    render_disclaimer()

    subjects = get_all_subjects()
    if not subjects:
        empty_state("No subjects or question papers have been ingested yet. Please contact the administrator or add papers via the Admin Portal.")
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

    # Low data warning check
    if any(p.get("low_data_warning") for p in predictions):
        n_yrs = predictions[0].get("data_years", 1)
        st.warning(f"⚠️ Only {n_yrs} year(s) of papers loaded — predictions are indicative. Load 3+ years for reliable scores.")

    # Metric summaries
    high_count = sum(1 for p in predictions if p["likelihood"] == "High")
    med_count = sum(1 for p in predictions if p["likelihood"] == "Medium")
    low_count = sum(1 for p in predictions if p["likelihood"] == "Low")

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Total Analyzed Clusters", len(predictions))
    col_m2.metric("High Likelihood (>=70%)", high_count)
    col_m3.metric("Medium Likelihood (45-69%)", med_count)
    col_m4.metric("Low Likelihood (<45%)", low_count)

    # Expander explaining the prediction formulas
    with st.expander("ℹ️ How predictions work"):
        st.markdown(
            """
            **Deterministic Multi-Factor Scoring Formula:**
            $$\\text{Final Score} = (0.35 \\times \\hat{F}) + (0.30 \\times \\hat{R}) + (0.20 \\times \\hat{G}) + (0.15 \\times \\hat{M})$$

            - **Frequency Weight ($w_f = 0.35$):** Distinct examination years the question appeared divided by total historical years examined.
            - **Recency Decay Weight ($w_r = 0.30$):** Exponential recency decay $\\sum e^{-0.3 \\times (\\text{current\\_year} - y)}$ with decay constant $\\lambda = 0.3$.
            - **Gap Cycle Weight ($w_g = 0.20$):** Cyclical repeat probability based on elapsed years since last appearance:
              - **Gap = 1 year:** $0.40$ (often rotated out)
              - **Gap = 2 years:** $1.00$ (highest historical repeat cycle)
              - **Gap = 3 years:** $0.85$ (medium-high recurrence)
              - **Gap $\\ge$ 4 years:** $0.50$ (long-tail rotation)
            - **Marks Weight ($w_m = 0.15$):** Normalized syllabus importance based on maximum marks observed.
            """
        )

    st.markdown("---")
    
    col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
    with col_act1:
        search_query = st.text_input("🔍 Search predicted questions by keyword", "")
    with col_act2:
        df_csv = pd.DataFrame([
            {
                "rank": idx + 1,
                "question_text": p["question_text"],
                "unit": p["unit"],
                "topic": p["topic"],
                "likelihood": p["likelihood"],
                "final_score": p["final_score"],
                "appearances_count": p["appearances_count"],
                "years_appeared": ", ".join(map(str, p["years_appeared"])),
            }
            for idx, p in enumerate(predictions)
        ])
        st.download_button(
            label="📊 Download CSV",
            data=df_csv.to_csv(index=False),
            file_name=f"{chosen_subj_name}_predictions.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_act3:
        if st.button("📥 Export Study PDF", use_container_width=True):
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
        years_str = safe(", ".join(map(str, p["years_appeared"])))
        c_contrib = p.get("contributions", {"frequency": 0, "recency": 0, "gap": 0, "marks": 0})

        with st.container():
            card_html = (
                f'<div style="background-color: rgba(128,128,128,0.10); border: 1px solid rgba(128,128,128,0.35); border-radius: 8px; padding: 14px; margin-bottom: 12px;">'
                f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">'
                f'<span style="font-weight: 600; font-size: 1.05rem;">Unit {p["unit"]} | {safe(p["topic"])} ({p["avg_marks"]} Marks)</span>'
                f'<span class="{badge_cls}">{safe(p["likelihood"])} ({p["final_score"]}%)</span>'
                f'</div>'
                f'<p style="font-size: 1rem; color: inherit; margin-bottom: 8px;">{safe(p["question_text"])}</p>'
                f'<div style="margin: 8px 0;">'
                f'<div style="display: flex; width: 100%; height: 8px; border-radius: 4px; overflow: hidden; background: rgba(128,128,128,0.25);">'
                f'<div style="width: {c_contrib["frequency"]}%; background: #007bff;" title="Frequency: {c_contrib["frequency"]}%"></div>'
                f'<div style="width: {c_contrib["recency"]}%; background: #28a745;" title="Recency: {c_contrib["recency"]}%"></div>'
                f'<div style="width: {c_contrib["gap"]}%; background: #ffc107;" title="Gap: {c_contrib["gap"]}%"></div>'
                f'<div style="width: {c_contrib["marks"]}%; background: #fd7e14;" title="Marks: {c_contrib["marks"]}%"></div>'
                f'</div>'
                f'<div style="display: flex; gap: 15px; font-size: 0.75rem; margin-top: 4px; opacity: 0.75;">'
                f'<span>🔵 Freq: {c_contrib["frequency"]}%</span>'
                f'<span>🟢 Recency: {c_contrib["recency"]}%</span>'
                f'<span>🟡 Gap: {c_contrib["gap"]}%</span>'
                f'<span>🟠 Marks: {c_contrib["marks"]}%</span>'
                f'</div>'
                f'</div>'
                f'<div style="font-size: 0.85rem; opacity: 0.7; margin-top: 6px;">'
                f'🗓️ <b>Appeared in:</b> {years_str} (Total: {p["appearances_count"]} times) | '
                f'⏳ <b>Gap:</b> {p["gap_years"]} yrs | '
                f'📊 <b>Freq Score:</b> {p["frequency_score"]}% | <b>Recency:</b> {p["recency_score"]}%'
                f'</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
            if p["image_path"] and os.path.exists(p["image_path"]):
                st.image(p["image_path"], caption=f"Original Exam Question Snippet (Cluster #{p['cluster_id']})", use_container_width=True)


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

        student_email = get_current_user_email()
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
                student_id=student_email if student_email else None,
            )
            if not items:
                st.error("No questions found matching your filter criteria. Please widen your syllabus unit selection.")
            else:
                init_quiz_session(items)
                st.session_state.active_quiz_subject_id = q_subj_id
                st.session_state.quiz_checked = {}
                st.rerun()

    else:
        # Running Quiz Session
        questions = st.session_state.quiz_questions
        idx = st.session_state.quiz_current_index
        total = len(questions)
        q = questions[idx]

        st.progress((idx) / total)
        st.caption(f"Question {idx + 1} of {total}")

        st.markdown(
            f"""
            <div style="background-color: rgba(128,128,128,0.10); border-left: 5px solid #28a745; padding: 14px; border-radius: 4px; margin-bottom: 15px;">
                <span style="font-size: 0.9rem; opacity: 0.7;">Unit {q['unit']} | {safe(q['topic'])} | Marks: {q['marks']}</span>
                <h4 style="margin-top: 5px; color: inherit;">{safe(q['question_text'])}</h4>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if q["image_path"] and os.path.exists(q["image_path"]):
            st.image(q["image_path"], caption="Original Question Snippet (Formulas, Symbols & Diagrams)", use_container_width=True)

        # Elapsed question timer
        elapsed_sec = int(time.time() - st.session_state.get("quiz_q_start_time", time.time()))
        st.caption(f"⏱️ Time on this question: {elapsed_sec}s")

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

        # Check answer interactive functionality
        if "quiz_checked" not in st.session_state:
            st.session_state.quiz_checked = {}
        is_checked = st.session_state.quiz_checked.get(idx, False)

        c_chk, _ = st.columns([1, 2])
        with c_chk:
            if st.button("🔍 Check Answer", key=f"btn_chk_{idx}", disabled=is_checked, use_container_width=True):
                if selected_radio:
                    st.session_state.quiz_checked[idx] = True
                    st.rerun()
                else:
                    st.warning("Please choose an option first.")

        if is_checked:
            chosen_opt = (selected_radio[0] if selected_radio else "")
            if chosen_opt == q["correct_option"]:
                st.success("✅ **Correct!** Excellent work.")
            elif chosen_opt == "E":
                st.info("⚪ Question marked as out of syllabus (skipped).")
            else:
                st.error(f"❌ **Incorrect.** Correct answer is **Option {q['correct_option']}**.")
            st.info(f"💡 **Explanation:** {safe(q['explanation'])}")

        # Next / Finish is enabled after the answer is checked OR option E (skip) is chosen
        can_proceed = is_checked or (selected_radio is not None and selected_radio.startswith("E"))

        col_nav1, col_nav2 = st.columns([1, 1])
        with col_nav1:
            if idx > 0:
                if st.button("⬅️ Previous Question", use_container_width=True):
                    st.session_state.quiz_current_index -= 1
                    st.rerun()

        with col_nav2:
            button_label = "Finish & Submit Quiz" if (idx == total - 1) else "Next Question ➡️"
            if st.button(button_label, type="primary", use_container_width=True, disabled=not can_proceed):
                if selected_radio:
                    chosen_letter = selected_radio[0]
                    elapsed = time.time() - st.session_state.quiz_q_start_time
                    st.session_state.quiz_responses[idx] = {
                        "selected_option": chosen_letter,
                        "duration": round(elapsed, 1),
                    }

                if idx == total - 1:
                    student_email = get_current_user_email()
                    if not student_email:
                        st.error("Please sign in or register with your student account in the sidebar to submit quiz attempts.")
                        st.stop()
                    student_id = student_email
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

    student_email = get_current_user_email()
    if not student_email:
        empty_state("Please sign in or register with your student account in the sidebar to view your diagnostic report and progress history.")
        st.stop()
    student_id = student_email

    last_attempt_id = st.session_state.get("last_attempt_id")
    history = get_student_history(student_id)

    if not last_attempt_id:
        if history:
            last_attempt_id = history[0]["id"]
        else:
            empty_state("No completed quiz attempts found for this account. Please complete a practice quiz first.")
            st.stop()

    report = analyze_attempt_performance(last_attempt_id)
    if "error" in report:
        st.error(report["error"])
        st.stop()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Overall Score", f"{report['score_percent']}%")
    col2.metric("Correct Answers", report["correct_count"])
    col3.metric("Mistakes", report["wrong_count"])
    col4.metric("Skipped (Out of Syllabus)", report["skipped_count"])

    st.markdown("---")
    
    # Progress line chart across attempts
    if history and len(history) > 1:
        st.subheader("📈 Score Progression Across Attempts")
        df_hist = pd.DataFrame([
            {"Attempt": f"#{h['id']} ({str(h['created_at'])[:10]})", "Score (%)": h["score"]}
            for h in reversed(history)
        ]).set_index("Attempt")
        st.line_chart(df_hist)

    # Strengths and Weaknesses
    c_str, c_wk = st.columns(2)
    with c_str:
        st.success("🌟 **Strong Knowledge Areas:**")
        if report["strengths"]:
            for s in report["strengths"]:
                st.markdown(f"- ✅ **{safe(s)}**")
        else:
            st.write("Complete more questions correctly to establish verified strengths.")

    with c_wk:
        st.error("⚠️ **High Priority Revision Areas:**")
        if report["weaknesses"]:
            for w in report["weaknesses"]:
                st.markdown(f"- 🚩 **{safe(w)}**")
        else:
            st.write("No critical weak spots detected!")

    st.markdown("### 🎯 Revision Priority Matrix (Weakness × Exam Likelihood)")
    st.write("This matrix weights the concepts you missed by how likely they are to appear on the exam:")

    # Topic Accuracy vs Priority Bar Chart
    active_topics = [t for t in report["topic_summary"] if not t.get("all_skipped")]
    if active_topics:
        df_bar = pd.DataFrame([
            {
                "Topic": t["topic"],
                "Accuracy (%)": (t["accuracy"] if t["accuracy"] is not None else 0.0),
                "Priority Score": t["priority_score"],
            }
            for t in active_topics
        ]).set_index("Topic")
        st.bar_chart(df_bar)

    if report["topic_summary"]:
        df_topics_disp = pd.DataFrame([
            {
                "Topic": t["topic"],
                "Unit": t["unit"],
                "Attempted": t["total_attempted"],
                "Correct": t["correct"],
                "Accuracy": f"{t['accuracy']}%" if t["accuracy"] is not None else "—",
                "Priority Score": t["priority_score"],
                "Average Likelihood": f"{t['avg_likelihood']}%",
                "Recommended Book": t["recommended_book"],
            }
            for t in report["topic_summary"]
        ])
        st.dataframe(df_topics_disp, use_container_width=True)

    # Skipped Topics Section (Skips never penalise)
    if report.get("skipped_topics"):
        st.markdown("#### 🚫 Marked as not in my syllabus")
        st.caption("These topics were marked as skipped in your quiz attempt and are excluded from accuracy penalties:")
        for sk_t in report["skipped_topics"]:
            st.markdown(f"- ⚪ **{safe(sk_t)}**")

    # Mistakes Review
    if report["mistakes"]:
        st.markdown("### 🔍 Mistakes Breakdown & Recommended Correction")
        for m in report["mistakes"]:
            with st.expander(f"❌ Question {safe(m['question_number'])} ({safe(m['topic'])})"):
                st.write(f"**Question:** {m['question_text']}")
                st.write(f"**Your Answer:** Option {m['selected_option']}")
                st.write(f"**Correct Answer:** Option {m['correct_option']}")
                st.info(f"💡 **Explanation & Book Pointer:** {m['explanation']}")

    # 1-Click Remedial Quiz
    if report["mistakes"]:
        st.markdown("---")
        if st.button("🔁 Launch 1-Click Remedial Quiz (Retry Failed Questions Only)", type="primary"):
            failed_q_ids = [m["question_id"] for m in report["mistakes"]]
            rem_items = load_questions_by_ids(failed_q_ids)
            if len(rem_items) < len(failed_q_ids):
                active_subj = st.session_state.get("active_quiz_subject_id", 1)
                generate_mcqs_for_subject(active_subj)
                rem_items = load_questions_by_ids(failed_q_ids)

            if rem_items:
                init_quiz_session(rem_items)
                st.session_state.quiz_checked = {}
                st.session_state.nav_selection = "📝 Practice Quiz & MCQ Bank"
                st.rerun()
            else:
                st.error("Unable to load remedial questions.")


# ==============================================================================
# VIEW 4: MOCK EXAM GENERATOR
# ==============================================================================
elif selected_page == "📑 Mock Exam Generator":
    st.title("📑 Blueprint-Compliant Mock Exam Paper Generator")
    render_disclaimer()

    subjects = get_all_subjects()
    if not subjects:
        empty_state("No subjects available. Ingest examination papers in the Admin Portal first.")
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

        # Warnings if any
        if paper.get("warnings"):
            for w in paper["warnings"]:
                st.warning(f"⚠️ {safe(w)}")

        # Examination Header
        dept_str = safe(paper.get("department") or "EXAMINATION")
        st.markdown(
            f"""
            <div style="text-align: center; border: 1px solid rgba(128,128,128,0.35); padding: 20px; border-radius: 8px; background-color: rgba(128,128,128,0.08); margin-bottom: 25px;">
                <h3 style="margin: 0; color: inherit;">{dept_str}</h3>
                <h4 style="margin: 5px 0; color: inherit;">{safe(paper['exam_type'])} EXAMINATION — SIMULATED PATTERN</h4>
                <p style="margin: 5px 0; opacity: 0.8;"><b>Subject:</b> {safe(paper['subject_name'])} ({safe(paper['subject_code'])}) | <b>Max Marks:</b> {paper['total_marks']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for sec in paper["sections"]:
            st.markdown(f"### {safe(sec['section_name'])}")
            st.markdown(f"*{safe(sec['instructions'])}*")
            for q in sec["questions"]:
                q_row_html = (
                    f'<div style="display: flex; justify-content: space-between; border-bottom: 1px dotted rgba(128,128,128,0.35); padding: 8px 0; margin-top: 10px;">'
                    f'<div>'
                    f'<b>{safe(q["q_num"])}.</b> {safe(q["text"])} '
                    f'<span style="font-size: 0.8rem; opacity: 0.7;">(Unit {q["unit"]} | Likelihood: {safe(q["likelihood"])})</span>'
                    f'</div>'
                    f'<div style="font-weight: bold; min-width: 60px; text-align: right;">[{int(q["marks"])} M]</div>'
                    f'</div>'
                )
                st.markdown(q_row_html, unsafe_allow_html=True)
                if q["image_path"] and os.path.exists(q["image_path"]):
                    st.image(q["image_path"], use_container_width=True)


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
        strictly on prior years (Years $< T$), and objectively measures the hit-rate of predicted questions 
        against the questions that actually appeared on that year's paper.
        """
    )

    subjects = get_all_subjects()
    if not subjects:
        empty_state("No subjects available for back-testing.")
        st.stop()

    subj_map = {s["name"]: s["id"] for s in subjects}

    col1, _ = st.columns([2, 2])
    with col1:
        bt_subj_name = st.selectbox("Select Subject", list(subj_map.keys()), key="bt_subj_select")
        bt_subj_id = subj_map.get(bt_subj_name)

    if not bt_subj_id:
        st.stop()

    # Query distinct years available for this subject
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT year FROM papers WHERE subject_id = ? AND year IS NOT NULL ORDER BY year ASC;",
            (bt_subj_id,),
        )
        avail_years = [r[0] for r in cursor.fetchall()]

    if len(avail_years) < 2:
        loaded_str = ", ".join(map(str, avail_years)) if avail_years else "None"
        st.info(f"Back-testing needs at least 2 years of papers for this subject. Currently loaded: {loaded_str}")
    else:
        # Rolling back-test comparison
        rolling_results = run_rolling_backtest(bt_subj_id)
        if rolling_results:
            st.subheader("📈 Rolling Back-Test Hit Rate vs. Recency Baseline")
            df_roll = pd.DataFrame(rolling_results).set_index("test_year")
            st.line_chart(df_roll[["hit_rate", "recency_baseline_hit_rate"]])
            st.caption("Empirical hit rate of multi-factor heuristics compared to naive most-recent appearance baseline.")

        st.markdown("---")
        st.subheader("🔎 Single-Year Detailed Simulation")
        test_year_cands = avail_years[1:]  # Needs at least 1 earlier year
        test_year = st.selectbox("Select Target Year to Simulate", test_year_cands, index=len(test_year_cands) - 1, key="bt_test_year")

        if st.button("🚀 Execute Back-Test Simulation", type="primary", use_container_width=True):
            with st.spinner("Simulating past paper predictions..."):
                results = run_historical_backtest(bt_subj_id, int(test_year))

            if not results["success"]:
                st.error(results["message"])
            else:
                c_res1, c_res2, c_res3, c_res4 = st.columns(4)
                c_res1.metric("Heuristic Hit-Rate", f"{results['hit_rate']}%")
                c_res2.metric("Recency Baseline", f"{results['recency_baseline_hit_rate']}%")
                c_res3.metric("Actual Paper Questions", results["total_actual"])
                c_res4.metric("Verified Hits", results["hits_count"])

                train_yrs_str = ", ".join(map(str, results.get("train_years", [])))
                st.caption(f"Training papers strictly used (years < {test_year}): {train_yrs_str}")

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

    tab_ingest, tab_inspect, tab_review, tab_mcqs, tab_edit, tab_tags, tab_manage, tab_db = st.tabs([
        "📥 Ingest Question Papers",
        "🔍 Pipeline Inspector",
        "🔍 Low-Confidence Review Queue",
        "📝 MCQ Bank Verification",
        "✏️ Edit Subjects, Papers & Questions",
        "🏷️ Tag & Syllabus Manager",
        "🗑️ Manage / Delete Papers & Subjects",
        "💾 System Maintenance & DB",
    ])

    # SUB-TAB 1: INGESTION PIPELINE
    with tab_ingest:
        st.subheader("Ingest Question Papers")

        ingest_mode = st.radio(
            "Ingestion Workflow",
            ["Combined PDF (auto-detect papers)", "Manual override (single paper)"],
            horizontal=True,
            key="rad_ingest_mode",
        )

        subjects = get_all_subjects()
        subject_names = [s["name"] for s in subjects]
        actor = get_current_user_email() or "diyanshah2301@gmail.com"

        if ingest_mode == "Combined PDF (auto-detect papers)":
            st.markdown("#### 📑 Combined PDF Intake & Auto-Segregation")
            st.caption("Upload a combined PDF containing one or multiple exam papers (up to 150 pages / 100 MB). The engine will automatically deskew, remove shadows, isolate papers, extract metadata, and parse questions.")

            uploaded_combined = st.file_uploader(
                "Upload Combined Exam PDF",
                type=["pdf"],
                key="uploader_combined_pdf",
                help="Max 150 pages and 100 MB. Supports camera scans and clean digital PDFs.",
            )

            if uploaded_combined:
                comb_bytes = uploaded_combined.read()
                st.info(f"Loaded: **{uploaded_combined.name}** ({round(len(comb_bytes)/(1024*1024), 2)} MB)")

                if st.button("🚀 Run Auto-Segregation & Ingestion", type="primary", key="btn_run_autoseg"):
                    with st.status("Processing document: Deskewing, illumination flattening, boundary detection & OCR...", expanded=True) as status:
                        def on_progress(msg, pct):
                            status.write(f"🔄 **{msg}** ({int(pct * 100)}%)")

                        success, msg, summary = ingest_combined_pdf(
                            file_bytes=comb_bytes,
                            original_filename=uploaded_combined.name,
                            actor_email=actor,
                            progress_callback=on_progress,
                        )

                        if success:
                            status.update(label="Auto-segregation and ingestion complete!", state="complete", expanded=False)
                            st.success(msg)
                            st.markdown("### 📋 Detected Examination Papers")
                            
                            for p in summary:
                                with st.container():
                                    c_th, c_info = st.columns([1, 3])
                                    with c_th:
                                        if p.get("thumbnail_path") and os.path.exists(p["thumbnail_path"]):
                                            st.image(p["thumbnail_path"], caption=f"Pages {p['page_range']}", use_container_width=True)
                                    with c_info:
                                        conf_val = p.get("metadata_confidence", 0.0)
                                        badge_color = "green" if conf_val >= 0.85 else "orange"
                                        st.markdown(f"#### {safe(p.get('subject_name', 'Unknown Course'))} (Paper ID #{p.get('paper_id')})")
                                        st.markdown(
                                            f"**Pages:** `{p['page_range']}` | "
                                            f"**Confidence:** :{badge_color}[{int(conf_val*100)}%] | "
                                            f"**Quality Score:** `{p.get('quality_score', 0.0)}` | "
                                            f"**Status:** `{p.get('status', 'accepted')}`"
                                        )
                                        st.markdown(f"**Extracted Questions:** `{p.get('questions_count', 0)}` questions committed.")
                                    st.divider()
                        else:
                            status.update(label="Ingestion failed", state="error", expanded=True)
                            st.error(msg)

        else:
            st.markdown("#### ✍️ Manual Single Paper Intake")
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
                                ok, dl_msg = download_drive_file(drive_url, temp_dl)
                                if ok:
                                    with open(temp_dl, "rb") as f:
                                        pdf_bytes = f.read()
                                    orig_filename = "drive_downloaded_paper.pdf"
                                    st.success("Document downloaded from Google Drive.")
                                else:
                                    st.error(f"Download failed: {dl_msg}")

                if pdf_bytes and st.button("⚡ Run Extraction & Ingestion Pipeline", type="primary"):
                    with st.status("Executing extraction and ingestion pipeline...", expanded=True) as status:
                        def on_manual_progress(msg, pct):
                            status.write(f"🔄 **{msg}** ({int(pct * 100)}%)")

                        success, msg, summary = process_pdf_document(
                            file_bytes=pdf_bytes,
                            original_filename=orig_filename,
                            subject_id=sel_subj_id,
                            year=int(in_year),
                            semester=int(in_sem),
                            exam_type=in_type,
                            actor_email=actor,
                            progress_callback=on_manual_progress,
                        )
                        if success:
                            status.update(label="Manual ingestion completed!", state="complete", expanded=False)
                            st.success(msg)
                            st.json(summary)
                        else:
                            status.update(label="Manual ingestion failed", state="error", expanded=True)
                            st.error(msg)

    # SUB-TAB 2: PIPELINE INSPECTOR
    with tab_inspect:
        st.subheader("🔍 Computer Vision Pipeline Inspector")
        st.caption("Inspect raw PDF page rendering, deskewing, shadow removal, and question bounding box overlays.")

        all_papers_insp = get_all_papers_detailed()
        if not all_papers_insp:
            empty_state("No papers available to inspect.")
        else:
            paper_labels = {
                f"Paper #{p['id']} - {p['subject_name']} ({p.get('year') or 'N/A'}, {p.get('exam_type') or 'N/A'})": p
                for p in all_papers_insp if p.get("file_path") and os.path.exists(p["file_path"])
            }
            if not paper_labels:
                empty_state("No physical PDF papers found in data/papers/.")
            else:
                sel_paper_label = st.selectbox("Select Paper to Inspect", list(paper_labels.keys()), key="inspect_paper_sel")
                sel_p = paper_labels[sel_paper_label]
                pdf_path = sel_p["file_path"]

                doc = pymupdf.open(pdf_path)
                total_pdf_pages = len(doc)
                page_choice = st.slider("Select Page Number", min_value=1, max_value=max(1, total_pdf_pages), value=1, key="inspect_page_slider")
                page = doc[page_choice - 1]

                # Render at 110 DPI (~1.527 zoom)
                zoom_factor = 110.0 / 72.0
                mat = pymupdf.Matrix(zoom_factor, zoom_factor)
                pix = page.get_pixmap(matrix=mat)
                nparr = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
                if pix.n >= 3:
                    raw_bgr = cv2.cvtColor(nparr[:, :, :3], cv2.COLOR_RGB2BGR)
                else:
                    raw_bgr = cv2.cvtColor(nparr, cv2.COLOR_GRAY2BGR)
                doc.close()

                # Call preprocessing pipeline
                prep_res = preprocess_page_image(raw_bgr)
                clean_bgr = prep_res["clean_bgr"]

                # Fetch bounding boxes for this paper and page
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT question_number, bbox_json FROM questions WHERE paper_id = ? AND page_no = ?;",
                        (sel_p["id"], page_choice),
                    )
                    q_boxes = [dict(r) for r in cursor.fetchall()]

                annotated_bgr = clean_bgr.copy()
                h_img, w_img = annotated_bgr.shape[:2]

                for qb in q_boxes:
                    qnum = qb.get("question_number") or ""
                    bbox_str = qb.get("bbox_json")
                    if bbox_str:
                        try:
                            box = json.loads(bbox_str)
                            if isinstance(box, list) and len(box) == 4:
                                x1, y1, x2, y2 = [int(v) for v in box]
                                x1 = max(0, min(w_img - 1, x1))
                                y1 = max(0, min(h_img - 1, y1))
                                x2 = max(0, min(w_img, x2))
                                y2 = max(0, min(h_img, y2))
                                cv2.rectangle(annotated_bgr, (x1, y1), (x2, y2), (0, 180, 0), 2)
                                cv2.putText(
                                    annotated_bgr,
                                    f"Q{qnum}",
                                    (x1, max(20, y1 - 6)),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.6,
                                    (0, 140, 0),
                                    2,
                                )
                        except Exception:
                            pass

                col_p1, col_p2, col_p3 = st.columns(3)
                with col_p1:
                    st.subheader("1. Original Render (110 DPI)")
                    st.image(cv2.cvtColor(raw_bgr, cv2.COLOR_BGR2RGB), use_container_width=True)
                with col_p2:
                    st.subheader(f"2. Cleaned Image (Score: {prep_res['quality_score']})")
                    st.image(cv2.cvtColor(clean_bgr, cv2.COLOR_BGR2RGB), use_container_width=True)
                with col_p3:
                    st.subheader(f"3. Question BBoxes ({len(q_boxes)})")
                    st.image(cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB), use_container_width=True)

    # SUB-TAB 2: REVIEW QUEUE
    with tab_review:
        st.subheader("🔍 Question Extraction & Confidence Review Queue")
        st.caption("Inspect, edit, and verify questions extracted across all subjects and past examination papers.")

        all_subs_review = get_all_subjects()
        col_f1, col_f2, col_f3 = st.columns([2, 2, 1])

        with col_f1:
            sub_filter_names = ["All Subjects"] + [s["name"] for s in all_subs_review]
            sel_sub_filter = st.selectbox("Filter by Subject", sub_filter_names, key="rev_sub_filter")
            chosen_sub_id = None
            if sel_sub_filter != "All Subjects":
                chosen_sub_id = next(s["id"] for s in all_subs_review if s["name"] == sel_sub_filter)

        with col_f2:
            status_filter_choice = st.selectbox(
                "Review Status",
                ["⚠️ Unreviewed & Needs Review", "📋 All Ingested Questions", "✅ Approved / Reviewed"],
                key="rev_status_filter"
            )
            status_arg = "unreviewed"
            if "All" in status_filter_choice:
                status_arg = "all"
            elif "Approved" in status_filter_choice:
                status_arg = "reviewed"

        with col_f3:
            page_size_choice = st.selectbox("Per Page", [10, 25, 50, "All"], index=1, key="rev_page_size")

        # Fetch questions based on user's exact filter
        review_questions = get_questions_for_review(subject_id=chosen_sub_id, status_filter=status_arg)
        all_db_tags = [t["name"] for t in get_all_tags(active_only=True)]

        col_act1, col_act2 = st.columns([3, 2])
        with col_act1:
            st.write(f"Showing **{len(review_questions)}** question(s) matching `{status_filter_choice}` for `{sel_sub_filter}`:")

        with col_act2:
            # 1-Click bulk approve high confidence
            unapproved_high = [q for q in review_questions if (q.get("confidence_score") or 0.0) >= 0.80 and not q.get("is_reviewed")]
            if unapproved_high:
                if st.button(f"⚡ Approve All High-Confidence ({len(unapproved_high)} Qs)", type="primary", key="btn_bulk_approve"):
                    cnt = approve_all_high_confidence_questions(subject_id=chosen_sub_id, threshold=0.80)
                    st.success(f"Approved {cnt} high-confidence questions!")
                    st.rerun()

        if not review_questions:
            if status_arg == "unreviewed":
                st.success("🎉 All extracted questions have been verified! Switch to 'All Ingested Questions' to browse all questions.")
            else:
                st.info("No questions found matching the selected filters.")
        else:
            # Pagination logic
            limit_val = len(review_questions) if page_size_choice == "All" else int(page_size_choice)
            total_pages = max(1, (len(review_questions) + limit_val - 1) // limit_val)
            
            if "rev_current_page" not in st.session_state:
                st.session_state.rev_current_page = 1
            if st.session_state.rev_current_page > total_pages:
                st.session_state.rev_current_page = total_pages

            cur_p = st.session_state.rev_current_page
            start_q_idx = (cur_p - 1) * limit_val
            end_q_idx = min(len(review_questions), start_q_idx + limit_val)
            page_slice = review_questions[start_q_idx:end_q_idx]

            # Render questions
            for q in page_slice:
                q_id = q["id"]
                conf_val = float(q.get("confidence_score") or 0.0)
                conf_pct = int(conf_val * 100)
                if conf_val >= 0.80:
                    badge_str = f":green[🟢 Confidence: {conf_pct}%]"
                elif conf_val >= 0.60:
                    badge_str = f":orange[🟡 Confidence: {conf_pct}%]"
                else:
                    badge_str = f":red[🔴 Low Confidence: {conf_pct}%]"

                approved_str = "✅ Approved" if q.get("is_reviewed") else "⚠️ Pending Review"

                st.markdown(
                    f"#### Question #{q['question_number']} | {q.get('subject_name', '')} ({q['year']} {q['exam_type'].upper()}) — {badge_str} | `{approved_str}`"
                )

                col_ed1, col_ed2 = st.columns([2, 1])
                with col_ed1:
                    new_text = st.text_area(
                        "Question Text",
                        q["question_text"],
                        key=f"rev_text_{q_id}",
                        height=110,
                    )
                    
                    # Display snippet or figure image if present
                    c_img1, c_img2 = st.columns(2)
                    with c_img1:
                        if q.get("image_path") and os.path.exists(q["image_path"]):
                            st.image(q["image_path"], caption=f"Question Snippet #{q['question_number']}", use_container_width=True)
                    with c_img2:
                        if q.get("figure_path") and os.path.exists(q["figure_path"]):
                            st.image(q["figure_path"], caption="Extracted Diagram/Figure", use_container_width=True)

                with col_ed2:
                    new_q_num = st.text_input("Question Label", value=str(q.get("question_number", "")), key=f"rev_qnum_{q_id}")
                    new_marks = st.number_input("Marks", value=float(q["marks"] or 5.0), min_value=1.0, max_value=30.0, step=0.5, key=f"rev_m_{q_id}")
                    new_unit = st.number_input("Unit", value=int(q["unit"] or 1), min_value=1, max_value=10, key=f"rev_u_{q_id}")
                    new_topic = st.text_input("Topic Name", value=q["topic"] or "General", key=f"rev_top_{q_id}")

                # INTERACTIVE GLOWING TOGGLE TAGS
                st.markdown("##### 🏷️ Assign / Toggle Tags (Multi-select with Green Glow):")
                current_assigned_tags = get_question_tags(q_id)
                session_tag_key = f"active_tags_q_{q_id}"
                if session_tag_key not in st.session_state:
                    st.session_state[session_tag_key] = set(current_assigned_tags)

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

                # Save and Approve Button
                if st.button(f"💾 Save & Approve Question #{q['question_number']}", key=f"btn_save_q_{q_id}", type="primary"):
                    final_tags = list(st.session_state[session_tag_key])
                    update_question_details(
                        question_id=q_id,
                        question_text=new_text,
                        marks=new_marks,
                        unit=new_unit,
                        topic=new_topic,
                        is_reviewed=True,
                        question_number=new_q_num,
                    )
                    update_question_tags(q_id, final_tags)
                    log_action(
                        actor=get_current_user_email(),
                        action="APPROVE_QUESTION",
                        details=f"Question ID {q_id} approved with tags {final_tags}.",
                    )
                    st.success(f"Question #{new_q_num} approved successfully!")
                    st.rerun()

                st.markdown("---")

            # Pagination Controls
            if total_pages > 1:
                c_prev, c_pg_info, c_next = st.columns([1, 2, 1])
                with c_prev:
                    if st.button("⬅️ Previous", disabled=(cur_p <= 1), key="btn_prev_page", use_container_width=True):
                        st.session_state.rev_current_page = max(1, cur_p - 1)
                        st.rerun()
                with c_pg_info:
                    st.markdown(f"<div style='text-align:center; padding-top:8px;'><b>Page {cur_p} of {total_pages}</b> (Showing {start_q_idx+1}-{end_q_idx} of {len(review_questions)})</div>", unsafe_allow_html=True)
                with c_next:
                    if st.button("Next ➡️", disabled=(cur_p >= total_pages), key="btn_next_page", use_container_width=True):
                        st.session_state.rev_current_page = min(total_pages, cur_p + 1)
                        st.rerun()

    # SUB-TAB 3: MCQ BANK VERIFICATION
    with tab_mcqs:
        st.subheader("📝 MCQ Bank Verification")
        st.caption("Review draft MCQs generated from exam questions and mark them as verified so students can practice with them.")

        all_subs_mcq = get_all_subjects()
        if not all_subs_mcq:
            st.info("No subjects available.")
        else:
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                sel_sub_mcq = st.selectbox("Select Subject", [s["name"] for s in all_subs_mcq], key="mcq_sub_sel")
                sub_id_mcq = next(s["id"] for s in all_subs_mcq if s["name"] == sel_sub_mcq)
            with col_s2:
                mcq_filter_status = st.selectbox("Filter Status", ["All", "draft", "verified"], key="mcq_stat_sel")

            c_gen, _ = st.columns([2, 1])
            with c_gen:
                if st.button("🤖 Generate rule-based MCQs for this subject", use_container_width=True):
                    counts = generate_mcqs_for_subject(sub_id_mcq)
                    st.success(f"Generated {counts['created']} rule-based MCQs ({counts['skipped']} questions skipped).")
                    st.info("ℹ️ Note: These rule-based MCQs test syllabus topic classification and command-verb task recognition, not domain answers.")
                    st.rerun()

            with st.expander("✍️ Write a Real MCQ Manually", expanded=False):
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT q.id, q.question_number, q.question_text, p.year
                        FROM questions q
                        JOIN papers p ON q.paper_id = p.id
                        WHERE p.subject_id = ?
                        ORDER BY q.id ASC;
                        """,
                        (sub_id_mcq,),
                    )
                    man_q_rows = [dict(r) for r in cursor.fetchall()]

                if man_q_rows:
                    q_choice_map = {f"Q#{r['question_number']} ({r['year']}) - {r['question_text'][:60]}...": r["id"] for r in man_q_rows}
                    sel_q_label = st.selectbox("Select Target Question", list(q_choice_map.keys()), key="man_q_sel")
                    sel_q_id = q_choice_map[sel_q_label]

                    man_opt_a = st.text_input("Option A", key="man_opt_a")
                    man_opt_b = st.text_input("Option B", key="man_opt_b")
                    man_opt_c = st.text_input("Option C", key="man_opt_c")
                    man_opt_d = st.text_input("Option D", key="man_opt_d")
                    man_correct = st.radio("Correct Option", ["A", "B", "C", "D"], horizontal=True, key="man_opt_correct")
                    man_exp = st.text_area("Explanation / Textbook Reference", key="man_opt_exp")

                    if st.button("💾 Submit Verified MCQ", type="primary", key="btn_submit_manual_mcq"):
                        if man_opt_a.strip() and man_opt_b.strip() and man_opt_c.strip() and man_opt_d.strip():
                            add_mcq(
                                question_id=sel_q_id,
                                option_a=man_opt_a,
                                option_b=man_opt_b,
                                option_c=man_opt_c,
                                option_d=man_opt_d,
                                correct_option=man_correct,
                                explanation=man_exp or "Manually verified question explanation.",
                                status="verified",
                                generator="manual",
                            )
                            st.success("Verified MCQ added successfully!")
                            st.rerun()
                        else:
                            st.error("Please fill in all options A through D.")

            filter_arg = None if mcq_filter_status == "All" else mcq_filter_status
            subject_mcqs = get_mcqs_for_subject(sub_id_mcq, status=filter_arg)
            # Exclude archived MCQs
            subject_mcqs = [m for m in subject_mcqs if m.get("status") != "archived"]

            if not subject_mcqs:
                st.info(f"No active MCQs found matching '{mcq_filter_status}' status for {sel_sub_mcq}.")
            else:
                st.write(f"Showing **{len(subject_mcqs)}** MCQ(s):")
                for mcq in subject_mcqs[:20]:
                    mcq_id = mcq["id"]
                    is_verified = (mcq.get("status") == "verified")
                    gen_name = mcq.get("generator") or "manual"
                    status_badge = f"{'✅ **Verified**' if is_verified else '🟡 **Draft**'} | `{gen_name}`"
                    
                    with st.expander(f"Question #{mcq.get('question_number', '')} ({mcq.get('marks')} Marks) — {status_badge}", expanded=not is_verified):
                        st.markdown(f"**Question:** {safe(mcq.get('question_text'))}")
                        st.markdown(f"- **A:** {safe(mcq.get('option_a'))}")
                        st.markdown(f"- **B:** {safe(mcq.get('option_b'))}")
                        st.markdown(f"- **C:** {safe(mcq.get('option_c'))}")
                        st.markdown(f"- **D:** {safe(mcq.get('option_d'))}")
                        st.markdown(f"**Correct Option:** `{mcq.get('correct_option')}`")
                        st.caption(f"Explanation: {safe(mcq.get('explanation'))}")

                        if not is_verified:
                            if st.button("✅ Mark as Verified", key=f"btn_verify_mcq_{mcq_id}", type="primary"):
                                verify_mcq(mcq_id)
                                st.success(f"MCQ #{mcq_id} verified successfully!")
                                st.rerun()

    # SUB-TAB 4: EDIT SUBJECTS, PAPERS & QUESTION SUBDETAILS
    with tab_edit:
        st.subheader("✏️ Edit Subjects, Papers & Question Subdetails")
        st.write("Modify names, syllabus codes, exam years, semesters, or any individual question's marks, text, unit, and tags.")

        edit_choice = st.radio(
            "Select What You Want to Edit:",
            ["📚 Edit Subject Details", "📄 Edit Exam Paper Subdetails", "❓ Edit Question Subdetails"],
            horizontal=True,
            key="edit_category_radio",
        )

        st.markdown("---")

        all_subs = get_all_subjects()
        if not all_subs:
            st.info("No subjects currently registered in the database.")
        else:
            sub_lookup = {s["name"]: s for s in all_subs}

            # 1. EDIT SUBJECT DETAILS
            if edit_choice == "📚 Edit Subject Details":
                st.markdown("#### 📚 Modify Subject Name & Syllabus Code")
                sel_sub_name = st.selectbox("Select Subject to Edit", list(sub_lookup.keys()), key="ed_sub_name_sel")
                sub_data = sub_lookup[sel_sub_name]

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    updated_name = st.text_input("Subject Full Name", value=sub_data["name"], key="input_ed_sub_name")
                with col_s2:
                    updated_code = st.text_input("Syllabus / Course Code (e.g., R5MA2007T)", value=sub_data["code"] or "", key="input_ed_sub_code")

                if st.button("💾 Save Subject Changes", type="primary", key="btn_save_sub_ed"):
                    if updated_name.strip():
                        update_subject(sub_data["id"], updated_name.strip(), updated_code.strip())
                        st.success(f"Subject '{updated_name}' successfully updated!")
                        st.rerun()
                    else:
                        st.error("Subject name cannot be empty.")

            # 2. EDIT EXAM PAPER SUBDETAILS
            elif edit_choice == "📄 Edit Exam Paper Subdetails":
                st.markdown("#### 📄 Modify Exam Paper Metadata (Year, Semester, Exam Type)")
                all_papers = get_all_papers_detailed()
                if not all_papers:
                    st.info("No papers currently ingested.")
                else:
                    paper_map = {
                        f"ID #{p['id']} - {p['subject_name']} ({p['year']} {p['exam_type'].upper()}) [Sem {p['semester']}]": p
                        for p in all_papers
                    }
                    sel_p_label = st.selectbox("Select Paper", list(paper_map.keys()), key="ed_paper_sel")
                    chosen_p = paper_map[sel_p_label]

                    col_p1, col_p2, col_p3 = st.columns(3)
                    with col_p1:
                        new_year = st.number_input("Year of Examination", min_value=2015, max_value=2030, value=int(chosen_p["year"]), key="ed_p_year")
                    with col_p2:
                        new_sem = st.number_input("Semester", min_value=1, max_value=8, value=int(chosen_p["semester"]), key="ed_p_sem")
                    with col_p3:
                        type_idx = 0 if chosen_p["exam_type"].lower() == "midterm" else 1
                        new_type = st.selectbox("Exam Type", ["midterm", "endterm"], index=type_idx, key="ed_p_type")

                    if st.button("💾 Save Paper Subdetails", type="primary", key="btn_save_p_ed"):
                        update_paper_details(chosen_p["id"], new_year, new_sem, new_type)
                        st.success(f"Paper ID #{chosen_p['id']} updated to {new_year} {new_type.upper()} (Sem {new_sem})!")
                        st.rerun()

            # 3. EDIT QUESTION SUBDETAILS
            elif edit_choice == "❓ Edit Question Subdetails":
                st.markdown("#### ❓ Modify Question Subdetails, Marks, Topic & Tags")
                all_papers = get_all_papers_detailed()
                if not all_papers:
                    st.info("No papers available.")
                else:
                    paper_map = {
                        f"ID #{p['id']} - {p['subject_name']} ({p['year']} {p['exam_type'].upper()})": p
                        for p in all_papers
                    }
                    sel_p_lbl = st.selectbox("Filter by Paper", list(paper_map.keys()), key="ed_q_paper_filter")
                    active_paper_id = paper_map[sel_p_lbl]["id"]

                    paper_questions = get_questions_by_paper(active_paper_id)
                    if not paper_questions:
                        st.warning("No questions found in this paper.")
                    else:
                        q_map = {
                            f"Q.{q['question_number']} (Unit {q['unit']}, {q['marks']}M) - {q['question_text'][:60]}...": q
                            for q in paper_questions
                        }
                        chosen_q_label = st.selectbox("Select Question to Edit", list(q_map.keys()), key="ed_q_sel")
                        q_to_edit = q_map[chosen_q_label]
                        q_id = q_to_edit["id"]

                        # Show visual snippet
                        if q_to_edit.get("image_path") and os.path.exists(q_to_edit["image_path"]):
                            st.image(q_to_edit["image_path"], caption="Current Question Visual Snippet", use_container_width=True)

                        c_q1, c_q2, c_q3 = st.columns(3)
                        with c_q1:
                            ed_q_num = st.text_input("Question Label (e.g. Q.1, Q.2)", value=str(q_to_edit["question_number"]), key=f"inp_q_num_{q_id}")
                        with c_q2:
                            ed_q_marks = st.number_input("Marks", min_value=1.0, max_value=30.0, step=0.5, value=float(q_to_edit["marks"]), key=f"inp_q_m_{q_id}")
                        with c_q3:
                            ed_q_unit = st.number_input("Unit", min_value=1, max_value=10, value=int(q_to_edit["unit"]), key=f"inp_q_u_{q_id}")

                        ed_q_topic = st.text_input("Topic Name", value=q_to_edit.get("topic") or "General", key=f"inp_q_top_{q_id}")
                        ed_q_text = st.text_area("Question Text", value=q_to_edit["question_text"], height=120, key=f"inp_q_txt_{q_id}")

                        # Interactive Glowing Tag Toggle
                        st.markdown("##### 🏷️ Assign / Toggle Tags (Multi-select with Green Glow):")
                        all_db_tags = [t["name"] for t in get_all_tags(active_only=True)]
                        current_tags = get_question_tags(q_id)
                        session_tag_key = f"ed_active_tags_{q_id}"
                        if session_tag_key not in st.session_state:
                            st.session_state[session_tag_key] = set(current_tags)

                        tag_cols = st.columns(6)
                        for t_idx, tag_name in enumerate(all_db_tags):
                            col_tgt = tag_cols[t_idx % 6]
                            is_active = tag_name in st.session_state[session_tag_key]
                            btn_label = f"✓ {tag_name}" if is_active else tag_name
                            with col_tgt:
                                if st.button(btn_label, key=f"btn_ed_tag_{q_id}_{tag_name}", use_container_width=True):
                                    if is_active:
                                        st.session_state[session_tag_key].remove(tag_name)
                                    else:
                                        st.session_state[session_tag_key].add(tag_name)
                                    st.rerun()

                        if st.button(f"💾 Save Changes for Question #{ed_q_num}", type="primary", key=f"btn_save_q_final_{q_id}"):
                            final_tags = list(st.session_state[session_tag_key])
                            update_question_details(
                                question_id=q_id,
                                question_text=ed_q_text,
                                marks=ed_q_marks,
                                unit=ed_q_unit,
                                topic=ed_q_topic,
                                is_reviewed=True,
                                question_number=ed_q_num,
                            )
                            update_question_tags(q_id, final_tags)
                            log_action(
                                actor=get_current_user_email(),
                                action="EDIT_QUESTION",
                                details=f"Question ID {q_id} modified: Q.{ed_q_num}, {ed_q_marks}M, Unit {ed_q_unit}, Topic '{ed_q_topic}'.",
                            )
                            st.success(f"Question #{ed_q_num} updated successfully!")
                            st.rerun()

    # SUB-TAB 4: TAG & SYLLABUS MANAGER
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

    # SUB-TAB 4: MANAGE & DELETE PAPERS / SUBJECTS
    with tab_manage:
        st.subheader("🗑️ Manage & Remove Ingested Papers or Subjects")
        st.write("Easily remove an incorrectly uploaded PDF paper or completely delete an outdated subject.")

        col_m_p, col_m_s = st.columns(2)

        # 1. DELETE SPECIFIC PAPER
        with col_m_p:
            st.markdown("### 📄 Remove a Specific Exam Paper (PDF)")
            all_papers = get_all_papers_detailed()
            if not all_papers:
                st.info("No exam papers are currently in the database.")
            else:
                paper_options = {
                    f"ID #{p['id']} - {p['subject_name']} ({p['year']} {p['exam_type'].upper()}) - {p['question_count']} Questions": p['id']
                    for p in all_papers
                }
                chosen_paper_label = st.selectbox("Select Paper to Delete", list(paper_options.keys()), key="del_paper_select")
                chosen_paper_id = paper_options[chosen_paper_label]

                st.warning("⚠️ Deleting a paper will permanently delete its PDF file, all extracted question snippet images, tags, and MCQs.")
                confirm_del_p = st.checkbox("Confirm permanent deletion of this paper", key="chk_confirm_p")
                if st.button("🗑️ Delete Selected Paper", type="primary", disabled=not confirm_del_p, key="btn_del_paper"):
                    ok = delete_paper(chosen_paper_id)
                    if ok:
                        st.success(f"Paper ID #{chosen_paper_id} and all related questions removed successfully.")
                        st.rerun()
                    else:
                        st.error("Failed to delete paper.")

        # 2. DELETE ENTIRE SUBJECT
        with col_m_s:
            st.markdown("### 📚 Remove an Entire Subject")
            all_subs = get_all_subjects()
            if not all_subs:
                st.info("No subjects are registered.")
            else:
                sub_options = {s["name"]: s["id"] for s in all_subs}
                chosen_sub_name = st.selectbox("Select Subject to Delete", list(sub_options.keys()), key="del_sub_select")
                chosen_sub_id = sub_options[chosen_sub_name]

                st.error(f"🚨 **Warning:** Deleting '{chosen_sub_name}' will permanently remove ALL associated PDF papers, question snippet images, past student quiz records, and syllabus settings.")
                confirm_del_s = st.checkbox("Confirm permanent deletion of this entire subject", key="chk_confirm_s")
                if st.button("🚨 Permanently Delete Subject", type="primary", disabled=not confirm_del_s, key="btn_del_sub"):
                    ok = delete_subject(chosen_sub_id)
                    if ok:
                        st.success(f"Subject '{chosen_sub_name}' and all associated papers/questions have been deleted.")
                        st.rerun()
                    else:
                        st.error("Failed to delete subject.")

    # SUB-TAB 5: DB MAINTENANCE & RECOMPUTE
    with tab_db:
        st.subheader("💾 Database Maintenance & Predictions Recomputation")
        
        st.write(
            """
            When new question papers are uploaded 2 or 3 years into the future, 
            click **Recompute All Predictions** below. The system recalculates all recurrence weights,
            updates recency exponential decays, and integrates newly joined diagram groups without altering existing tags.
            """
        )

        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            if st.button("🔄 Recompute All Predictions", type="primary", use_container_width=True):
                all_subs = get_all_subjects()
                for s in all_subs:
                    calculate_cluster_predictions(s["id"])
                st.success("All predictions successfully recomputed with updated recency and gap scores.")

        with col_b2:
            orphan_info = preview_orphans()
            st.caption(f"Orphan rows detected: {orphan_info['orphaned_mcqs']} MCQs, {orphan_info['unused_diagram_groups']} unused groups.")
            clean_confirmed = st.checkbox("I understand these rows will be exported then removed", key="chk_orphan_clean")
            if st.button("🧹 Clean Orphaned Records", use_container_width=True, disabled=not clean_confirmed):
                stats = cleanup_orphans(confirm=True)
                if stats.get("success"):
                    st.success(f"Backed up to `{os.path.basename(stats['backup_path'])}` and cleaned {stats['orphaned_mcqs']} MCQs, {stats['unused_diagram_groups']} groups.")
                    st.rerun()
                else:
                    st.error(stats.get("message", "Failed to clean orphans."))

        with col_b3:
            db_json = export_database_json()
            st.download_button(
                label="📦 Download Database Backup",
                data=db_json,
                file_name=f"exam_predictor_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
            )
