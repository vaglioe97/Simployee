import streamlit as st
from core.database import get_user_progress, get_tasks
from core.job_paths import get_job_path

st.set_page_config(page_title="Progress · Simployee", page_icon="📈", layout="centered")

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
total_weeks = path["duration_weeks"]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📈 Your Progress")
st.caption(f"{path['title']} at {path['company']}")
st.divider()

# ── Overall progress bar ──────────────────────────────────────────────────────
pct = round((week - 1) / total_weeks * 100)
st.subheader(f"Week {week} of {total_weeks}")
st.progress((week - 1) / total_weeks)
st.caption(f"{pct}% through the program · {total_weeks - week + 1} weeks remaining")
st.divider()

# ── Stats ─────────────────────────────────────────────────────────────────────
all_tasks = []
for w in range(1, week + 1):
    tasks = get_tasks(user["id"], w)
    all_tasks.extend([dict(t) for t in tasks])

total_tasks = len(all_tasks)
completed = sum(1 for t in all_tasks if t["status"] == "reviewed")
pending = sum(1 for t in all_tasks if t["status"] == "pending")
submitted = sum(1 for t in all_tasks if t["status"] == "submitted")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Weeks Completed", week - 1)
col2.metric("Tasks Completed", completed)
col3.metric("Tasks Pending", pending)
col4.metric("Weeks Remaining", total_weeks - week + 1)

st.divider()

# ── Weekly breakdown ──────────────────────────────────────────────────────────
st.subheader("Weekly Breakdown")

for w in range(1, week + 1):
    tasks = [dict(t) for t in get_tasks(user["id"], w)]

    if not tasks:
        continue

    reviewed = sum(1 for t in tasks if t["status"] == "reviewed")
    total = len(tasks)
    week_complete = reviewed == total

    status_label = "✅ Complete" if week_complete else "🔵 In Progress"

    with st.expander(f"Week {w} — {status_label} ({reviewed}/{total} tasks done)"):
        for task in tasks:
            icon = {"pending": "🔵", "submitted": "🟡", "reviewed": "✅"}.get(task["status"], "🔵")
            st.markdown(f"{icon} **{task['title']}**")
            if task["status"] == "reviewed" and task["feedback"]:
                st.caption(f"Feedback received from {path['manager']}")

st.divider()

# ── Role info ─────────────────────────────────────────────────────────────────
st.subheader("Your Role")
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**Position:** {path['title']}")
    st.markdown(f"**Company:** {path['company']}")
    st.markdown(f"**Manager:** {path['manager']}")
with col2:
    st.markdown(f"**Industry:** {path['industry']}")
    st.markdown(f"**Level:** {path['level']}")
    st.markdown(f"**Stack:** {', '.join(path['stack'])}")