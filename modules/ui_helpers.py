import html
from typing import Any
import streamlit as st


def safe(value: Any) -> str:
    """Escapes HTML entities and converts newlines to <br> for safe markdown embedding."""
    return html.escape(str(value if value is not None else ""), quote=True).replace("\n", "<br>")


def empty_state(message: str) -> None:
    """Renders a consistent, theme-neutral empty state placeholder banner."""
    st.markdown(
        f"""
        <div style="
            text-align: center;
            padding: 30px 20px;
            background-color: rgba(128, 128, 128, 0.08);
            border: 1px dashed rgba(128, 128, 128, 0.35);
            border-radius: 8px;
            margin: 15px 0;
            opacity: 0.85;
        ">
            <span style="font-size: 1.1rem; color: inherit;">ℹ️ {safe(message)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
