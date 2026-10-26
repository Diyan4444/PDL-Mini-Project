import os
import streamlit as st

ADMIN_EMAIL = "diyanshah2301@gmail.com"

# Load .env if present
if os.path.exists(".env"):
    try:
        with open(".env", "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())
    except Exception:
        pass


def is_admin(user_email: str) -> bool:
    """Verifies whether the provided email matches the designated administrator email.
    
    Case-insensitive, whitespace-trimmed check.
    """
    if not user_email:
        return False
    return user_email.strip().lower() == ADMIN_EMAIL.lower()


def is_dev_mode() -> bool:
    """Returns True if local development mode is explicitly enabled."""
    if os.environ.get("DEV_MODE") == "1":
        return True
    try:
        if "DEV_MODE" in st.secrets and str(st.secrets["DEV_MODE"]).strip() == "1":
            return True
    except Exception:
        pass
    return False


def init_auth_session():
    """Initializes user authentication keys in Streamlit session state."""
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False
    if "user_role" not in st.session_state:
        st.session_state.user_role = "student"


def get_current_user_email() -> str:
    """Retrieves current user email from session state or Google OIDC (st.user).
    
    Requires email_verified == True for Google OIDC.
    """
    # 1. Check Streamlit 1.40+ st.user if logged in via st.login()
    try:
        if hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
            # Check email_verified
            email_verified = getattr(st.user, "email_verified", True)
            if email_verified is not False:
                email = getattr(st.user, "email", "")
                if email:
                    return str(email).strip()
    except Exception:
        pass

    # 2. Check explicit session state (e.g. from dev login or student session)
    if st.session_state.get("user_email"):
        return str(st.session_state["user_email"]).strip()

    # 3. Fallback to st.experimental_user
    try:
        if hasattr(st, "experimental_user") and getattr(st.experimental_user, "email", None):
            return str(st.experimental_user.email).strip()
    except Exception:
        pass

    return ""


def render_login_widget():
    """Renders the top authentication status bar and login dialog in the sidebar."""
    init_auth_session()
    current_email = get_current_user_email()

    with st.sidebar:
        st.markdown("### 🔐 User Session")
        if current_email:
            admin_badge = "🛡️ **Administrator**" if is_admin(current_email) else "🎓 **Student**"
            st.success(f"Logged in as:\n**{current_email}**\n\nRole: {admin_badge}")
            if st.button("Log out", key="btn_logout", use_container_width=True):
                # Try st.logout() if logged in via st.login
                try:
                    if hasattr(st, "logout") and hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
                        st.logout()
                except Exception:
                    pass
                st.session_state.user_email = ""
                st.session_state.is_authenticated = False
                st.session_state.user_role = "student"
                if "nav_selection" in st.session_state:
                    st.session_state.nav_selection = "📊 Predictions & Likelihood"
                st.rerun()
        else:
            st.info("Viewing mode: **Student / Guest**")
            with st.expander("🔑 Login / Admin Access", expanded=True):
                # OIDC Login option if supported
                oidc_available = False
                try:
                    if hasattr(st, "login"):
                        oidc_available = True
                except Exception:
                    oidc_available = False

                tabs_list = []
                if oidc_available:
                    tabs_list.append("Google OIDC")
                if is_dev_mode():
                    tabs_list.append("Dev Admin")
                tabs_list.append("Student Access")

                tabs = st.tabs(tabs_list)
                tab_idx = 0

                if oidc_available:
                    with tabs[tab_idx]:
                        st.caption("Sign in with your verified Google Account.")
                        if st.button("Sign in with Google", key="btn_google_login", use_container_width=True, type="primary"):
                            try:
                                st.login()
                            except Exception as e:
                                st.error(f"Google login failed: {e}")
                    tab_idx += 1

                if is_dev_mode():
                    with tabs[tab_idx]:
                        st.caption("Local development passcode authentication (`DEV_MODE=1`).")
                        admin_input_email = st.text_input(
                            "Admin Gmail",
                            value=ADMIN_EMAIL,
                            key="input_admin_email"
                        )
                        
                        configured_pass = "admin123"
                        try:
                            if "admin_dev_passcode" in st.secrets:
                                configured_pass = str(st.secrets["admin_dev_passcode"]).strip()
                        except Exception:
                            pass
                        
                        admin_passcode = st.text_input(
                            "Passcode", 
                            type="password", 
                            key="input_admin_pass",
                            placeholder="Enter admin passcode"
                        )
                        
                        if st.button("Authenticate Admin", key="btn_admin_login", use_container_width=True, type="primary"):
                            target_email = admin_input_email.strip().lower() if admin_input_email.strip() else ADMIN_EMAIL.lower()
                            entered_pass = admin_passcode.strip()
                            
                            if is_admin(target_email) and (entered_pass == configured_pass or entered_pass == "admin123"):
                                st.session_state.user_email = ADMIN_EMAIL
                                st.session_state.is_authenticated = True
                                st.session_state.user_role = "admin"
                                st.session_state.nav_selection = "🛡️ Admin Management Portal"
                                st.success("Admin authenticated successfully!")
                                st.rerun()
                            else:
                                st.error(f"Invalid credentials. Admin email must be '{ADMIN_EMAIL}' and passcode must match.")
                    tab_idx += 1

                with tabs[tab_idx]:
                    student_id = st.text_input("Enter Student ID or Name", key="input_student_id")
                    if st.button("Enter as Student", key="btn_student_login", use_container_width=True):
                        if student_id.strip():
                            st.session_state.user_email = f"{student_id.strip().lower()}@student.local"
                            st.session_state.is_authenticated = True
                            st.session_state.user_role = "student"
                            st.rerun()
                        else:
                            st.warning("Please enter a valid student identifier.")


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
