import streamlit as st
from core.database import init_db, create_user, get_user, get_user_progress, create_user_progress
from core.job_paths import get_all_paths, get_job_path
import hashlib

# Initialize database
init_db()

# Page config
st.set_page_config(
    page_title="Simployee",
    page_icon="💼",
    layout="centered"
)

# ── Session state defaults ────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "login"

# ── Helpers ───────────────────────────────────────────────────────────────────
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login(username, password):
    user = get_user(username)
    if user and user["password"] == hash_password(password):
        st.session_state.logged_in = True
        st.session_state.user = dict(user)
        return True
    return False

def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.page = "login"

# ── UI ────────────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:

    st.title("💼 Simployee")
    st.caption("Simulate a real job. Build real experience.")
    st.divider()

    tab_login, tab_register = st.tabs(["Log In", "Create Account"])

    with tab_login:
        st.subheader("Welcome back")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Log In", use_container_width=True):
            if login(username, password):
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tab_register:
        st.subheader("Start your journey")
        full_name = st.text_input("Full Name", key="reg_name")
        new_username = st.text_input("Username", key="reg_user")
        new_password = st.text_input("Password", type="password", key="reg_pass")
        confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")

        if st.button("Create Account", use_container_width=True):
            if not full_name or not new_username or not new_password:
                st.error("Please fill in all fields.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                success = create_user(new_username, hash_password(new_password), full_name)
                if success:
                    st.success("Account created! Please log in.")
                else:
                    st.error("Username already taken. Try another one.")

else:
    # ── Logged in ─────────────────────────────────────────────────────────────
    user = st.session_state.user
    progress = get_user_progress(user["id"])

    st.title("💼 Simployee")
    st.caption(f"Welcome, {user['full_name']} 👋")
    st.divider()

    if progress is None:
        # User hasn't picked a job path yet
        st.subheader("Choose your job path")
        st.write("Select the role you want to simulate. This will define your tasks and responsibilities for the next 24 weeks.")
        st.write("")

        paths = get_all_paths()
        for path in paths:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{path['title']}** at *{path['company']}*")
                    st.caption(f"{path['industry']} · {path['level']} · {path['duration_weeks']} weeks")
                    st.write(path['description'])
                    st.caption(f"Stack: {', '.join(path['stack'])}")
                with col2:
                    if st.button("Select", key=path['id'], use_container_width=True):
                        create_user_progress(user["id"], path["id"])
                        st.success(f"You've been hired as {path['title']} at {path['company']}!")
                        st.rerun()

    else:
        # User has a job path — show dashboard
        path = get_job_path(progress["job_path_id"])
        week = progress["current_week"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Role", path["title"])
        col2.metric("Company", path["company"])
        col3.metric("Week", f"{week} / {path['duration_weeks']}")

        st.divider()
        st.subheader("Your workspace")
        st.info(f"👔 Your manager is **{path['manager']}** ({path['manager_title']}). Head to the **Tasks** page to see your work for this week.")

        st.write("")
        if st.button("🚪 Log Out", use_container_width=False):
            logout()
            st.rerun()