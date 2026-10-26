import hmac
import os
import time
import streamlit as st
from modules.database import create_student_account, verify_student_account

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


def verify_dev_admin(email: str, passcode: str, configured_pass: str) -> bool:
    """Verifies dev admin credentials using hmac.compare_digest on UTF-8 bytes.
    
    Returns False if configured_pass, email, or passcode is empty, or email is not admin.
    """
    if not configured_pass or not email or not passcode:
        return False
    if not is_admin(email):
        return False
    return hmac.compare_digest(passcode.encode("utf-8"), configured_pass.encode("utf-8"))


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
                        
                        configured_pass = ""
                        try:
                            if "admin_dev_passcode" in st.secrets:
                                configured_pass = str(st.secrets["admin_dev_passcode"]).strip()
                        except Exception:
                            pass
                        if not configured_pass:
                            configured_pass = os.environ.get("ADMIN_DEV_PASSCODE", "").strip()

                        if not configured_pass:
                            st.warning("Dev admin login disabled: set admin_dev_passcode in .streamlit/secrets.toml")
                        else:
                            now = time.time()
                            locked_until = st.session_state.get("admin_locked_until", 0.0)
                            if now < locked_until:
                                remaining = int(locked_until - now)
                                st.error(f"Dev admin locked out due to repeated failures. Try again in {remaining}s.")
                            else:
                                admin_input_email = st.text_input(
                                    "Admin Gmail",
                                    value=ADMIN_EMAIL,
                                    key="input_admin_email"
                                )
                                admin_passcode = st.text_input(
                                    "Passcode", 
                                    type="password", 
                                    key="input_admin_pass",
                                    placeholder="Enter admin passcode"
                                )
                                if st.button("Authenticate Admin", key="btn_admin_login", use_container_width=True, type="primary"):
                                    target_email = admin_input_email.strip().lower() if admin_input_email.strip() else ADMIN_EMAIL.lower()
                                    entered_pass = admin_passcode.strip()
                                    
                                    if verify_dev_admin(target_email, entered_pass, configured_pass):
                                        st.session_state.user_email = ADMIN_EMAIL
                                        st.session_state.is_authenticated = True
                                        st.session_state.user_role = "admin"
                                        st.session_state.admin_fail_count = 0
                                        st.session_state.admin_locked_until = 0.0
                                        st.session_state.nav_selection = "🛡️ Admin Management Portal"
                                        st.success("Admin authenticated successfully!")
                                        st.rerun()
                                    else:
                                        fails = st.session_state.get("admin_fail_count", 0) + 1
                                        st.session_state.admin_fail_count = fails
                                        if fails >= 5:
                                            st.session_state.admin_locked_until = time.time() + 60.0
                                            st.session_state.admin_fail_count = 0
                                            st.error("Too many failed attempts. Locked for 60 seconds.")
                                        else:
                                            st.error(f"Invalid credentials ({5 - fails} attempts remaining).")
                    tab_idx += 1

                with tabs[tab_idx]:
                    st.caption("Sign in with your student account or register a new one.")
                    stu_tab_in, stu_tab_reg = st.tabs(["Sign In", "Register"])
                    
                    with stu_tab_in:
                        s_id = st.text_input("Student ID", key="input_student_id")
                        s_pass = st.text_input("Password", type="password", key="input_student_pass")
                        if st.button("Sign In as Student", key="btn_student_signin", use_container_width=True, type="primary"):
                            if verify_student_account(s_id, s_pass):
                                st.session_state.user_email = f"{s_id.strip().lower()}@student.local"
                                st.session_state.is_authenticated = True
                                st.session_state.user_role = "student"
                                st.success("Signed in successfully!")
                                st.rerun()
                            else:
                                st.error("Invalid student ID or password.")
                                
                    with stu_tab_reg:
                        reg_id = st.text_input("Student ID (3-30 chars, [a-z0-9_.-])", key="reg_student_id")
                        reg_name = st.text_input("Display Name", key="reg_student_name")
                        reg_pass = st.text_input("Password (min 8 chars)", type="password", key="reg_student_pass")
                        reg_confirm = st.text_input("Confirm Password", type="password", key="reg_student_pass_confirm")
                        if st.button("Register Account", key="btn_student_register", use_container_width=True):
                            if reg_pass != reg_confirm:
                                st.error("Passwords do not match.")
                            else:
                                ok, msg = create_student_account(reg_id, reg_name, reg_pass)
                                if ok:
                                    st.session_state.user_email = f"{reg_id.strip().lower()}@student.local"
                                    st.session_state.is_authenticated = True
                                    st.session_state.user_role = "student"
                                    st.success("Account registered and logged in!")
                                    st.rerun()
                                else:
                                    st.error(msg)


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
