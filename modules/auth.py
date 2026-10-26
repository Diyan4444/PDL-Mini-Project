import streamlit as st

ADMIN_EMAIL = "diyanshah2301@gmail.com"


def is_admin(user_email: str) -> bool:
    """Verifies whether the provided email matches the designated administrator email.
    
    Case-insensitive, whitespace-trimmed check.
    """
    if not user_email:
        return False
    return user_email.strip().lower() == ADMIN_EMAIL.lower()


def init_auth_session():
    """Initializes user authentication keys in Streamlit session state."""
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False
    if "user_role" not in st.session_state:
        st.session_state.user_role = "student"


def get_current_user_email() -> str:
    """Retrieves current user email from OAuth or local session state."""
    # Check Streamlit experimental_user / user if OAuth is enabled
    try:
        if hasattr(st, "experimental_user") and st.experimental_user.email:
            return st.experimental_user.email
        if hasattr(st, "user") and hasattr(st.user, "email") and st.user.email:
            return st.user.email
    except Exception:
        pass
    
    return st.session_state.get("user_email", "")


def render_login_widget():
    """Renders the top authentication status bar and login dialog."""
    init_auth_session()
    current_email = get_current_user_email()

    with st.sidebar:
        st.markdown("### 🔐 User Session")
        if current_email:
            admin_badge = "🛡️ **Administrator**" if is_admin(current_email) else "🎓 **Student**"
            st.success(f"Logged in as:\n**{current_email}**\n\nRole: {admin_badge}")
            if st.button("Log out", key="btn_logout", use_container_width=True):
                st.session_state.user_email = ""
                st.session_state.is_authenticated = False
                st.session_state.user_role = "student"
                st.rerun()
        else:
            st.info("You are currently viewing as **Guest/Student**.")
            with st.expander("🔑 Login / Admin Access", expanded=False):
                tab_student, tab_admin = st.tabs(["Student Access", "Admin Login"])
                
                with tab_student:
                    student_id = st.text_input("Enter Student ID or Name", key="input_student_id")
                    if st.button("Enter as Student", key="btn_student_login", use_container_width=True):
                        if student_id.strip():
                            st.session_state.user_email = f"{student_id.strip().lower()}@student.local"
                            st.session_state.is_authenticated = True
                            st.session_state.user_role = "student"
                            st.rerun()
                        else:
                            st.warning("Please enter a valid identifier.")
                
                with tab_admin:
                    admin_input_email = st.text_input(
                        "Admin Gmail",
                        placeholder=ADMIN_EMAIL,
                        key="input_admin_email"
                    )
                    
                    # Fetch dev passcode from secrets or default fallback
                    configured_pass = "admin123"
                    try:
                        if "admin_dev_passcode" in st.secrets:
                            configured_pass = st.secrets["admin_dev_passcode"]
                    except Exception:
                        pass
                    
                    admin_passcode = st.text_input("Passcode", type="password", key="input_admin_pass")
                    
                    if st.button("Authenticate Admin", key="btn_admin_login", use_container_width=True):
                        if is_admin(admin_input_email) and admin_passcode == configured_pass:
                            st.session_state.user_email = admin_input_email.strip().lower()
                            st.session_state.is_authenticated = True
                            st.session_state.user_role = "admin"
                            st.success("Admin authenticated successfully.")
                            st.rerun()
                        else:
                            st.error("Invalid admin credentials or unauthorized email address.")


def require_admin() -> bool:
    """Enforces server-side administrator authorization.
    
    Returns True if user is the verified admin; otherwise renders error and stops.
    """
    current_email = get_current_user_email()
    if not is_admin(current_email):
        st.error("🚫 **Access Denied**: This section requires Administrator authorization (`diyanshah2301@gmail.com`).")
        st.info("Please authenticate with the admin credentials in the sidebar to access administrative tools.")
        return False
    return True
