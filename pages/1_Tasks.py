import streamlit as st
import pandas as pd
import os
from core.database import (
    get_user_progress, get_tasks, save_task,
    submit_task, save_feedback, advance_week
)
from core.job_paths import get_job_path
from core.ai_engine import generate_weekly_tasks, evaluate_submission

st.set_page_config(page_title="Tasks · Simployee", page_icon="📋", layout="centered")

# ── Auth guard ────────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please log in first.")
    st.stop()

user = st.session_state.user
progress = get_user_progress(user["id"])

if progress is None:
    st.warning("Please select a job path first.")
    st.stop()

path = get_job_path(progress["job_path_id"])
week = progress["current_week"]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📋 Weekly Tasks")
st.caption(f"Week {week} · {path['title']} at {path['company']}")
st.divider()

# ── Dataset download ──────────────────────────────────────────────────────────
dataset_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'novaretail_sales_q1_2024.csv')
if os.path.exists(dataset_path):
    with open(dataset_path, 'rb') as f:
        csv_bytes = f.read()
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**📂 NovaRetail Sales Dataset — Q1 2024**")
            st.caption("500 rows · sales table · Use this for your SQL and Python tasks")
        with col2:
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_bytes,
                file_name="novaretail_sales_q1_2024.csv",
                mime="text/csv",
                use_container_width=True
            )
    st.divider()

# ── Load or generate tasks ────────────────────────────────────────────────────
tasks = get_tasks(user["id"], week)

if not tasks:
    st.info(f"No tasks yet for Week {week}. Click below to generate your work for this week.")
    if st.button("⚡ Generate Week Tasks", use_container_width=True):
        with st.spinner("Sophie Chen is preparing your tasks for this week..."):
            try:
                generated = generate_weekly_tasks(path, week)
                for task in generated:
                    save_task(
                        user["id"], week,
                        task["title"],
                        task["description"],
                        task["deliverable"]
                    )
                st.success("Tasks generated!")
                st.rerun()
            except Exception as e:
                st.error(f"Error generating tasks: {e}")
else:
    tasks = [dict(t) for t in tasks]
    all_reviewed = all(t["status"] == "reviewed" for t in tasks)

    # ── Task selector ─────────────────────────────────────────────────────────
    task_labels = []
    for i, t in enumerate(tasks):
        icon = {"pending": "🔵", "submitted": "🟡", "reviewed": "✅"}.get(t["status"], "🔵")
        task_labels.append(f"{icon} Task {i+1}: {t['title']}")

    selected_index = st.radio(
        "Select a task to work on:",
        range(len(tasks)),
        format_func=lambda i: task_labels[i]
    )

    st.divider()
    task = tasks[selected_index]

    # ── Task detail ───────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown(f"### {task['title']}")
        st.markdown("**Description**")
        st.write(task["description"])
        st.markdown("**Deliverable**")
        st.info(task["deliverable"])

    st.write("")

    # ── Submission ────────────────────────────────────────────────────────────
    if task["status"] == "pending":
        st.markdown("**Your submission**")

        submission_text = st.text_area(
            "Code, SQL query, written analysis, or comments",
            height=150,
            placeholder="Paste your code, query, or explain what you did...",
            key=f"text_{task['id']}"
        )

        uploaded_file = st.file_uploader(
            "Attach a file (Excel, CSV, Python script, etc.)",
            type=["xlsx", "xls", "csv", "py", "sql", "txt"],
            key=f"file_{task['id']}"
        )

        if uploaded_file:
            st.caption(f"📎 {uploaded_file.name} attached")

        if st.button("Submit", use_container_width=True):
            has_text = submission_text.strip()
            has_file = uploaded_file is not None

            if not has_text and not has_file:
                st.error("Please submit something — text, code, or a file.")
            else:
                file_content = None
                file_name = None

                if uploaded_file:
                    file_name = uploaded_file.name
                    try:
                        if uploaded_file.name.endswith(".csv"):
                            df = pd.read_csv(uploaded_file)
                            file_content = df.to_string(max_rows=100)
                        elif uploaded_file.name.endswith((".xlsx", ".xls")):
                            df = pd.read_excel(uploaded_file)
                            file_content = df.to_string(max_rows=100)
                        else:
                            file_content = uploaded_file.read().decode("utf-8", errors="ignore")
                    except Exception as e:
                        file_content = f"Could not read file: {e}"

                submission_record = submission_text if submission_text else f"[File submitted: {file_name}]"
                if file_name and submission_text:
                    submission_record = f"[File: {file_name}]\n\n{submission_text}"

                submit_task(task["id"], submission_record)

                with st.spinner("Sophie Chen is reviewing your work..."):
                    feedback = evaluate_submission(
                        task,
                        submission_text,
                        path,
                        file_content=file_content,
                        file_name=file_name
                    )
                    save_feedback(task["id"], feedback)
                st.rerun()

    elif task["status"] == "submitted":
        st.markdown("**Your submission**")
        st.code(task["submission"])
        st.info("Waiting for feedback...")

    elif task["status"] == "reviewed":
        st.markdown("**Your submission**")
        st.code(task["submission"])
        st.markdown("**Feedback from Sophie Chen**")
        st.success(task["feedback"])

    # ── Advance week ──────────────────────────────────────────────────────────
    st.divider()
    if all_reviewed:
        st.success("🎉 All tasks completed for this week!")
        if week < path["duration_weeks"]:
            if st.button("➡️ Advance to Next Week", use_container_width=True):
                advance_week(user["id"])
                st.rerun()
        else:
            st.balloons()
            st.success("🏆 You completed the full 24-week program!")
    else:
        pending = sum(1 for t in tasks if t["status"] != "reviewed")
        st.caption(f"{pending} task(s) remaining before you can advance to the next week.")