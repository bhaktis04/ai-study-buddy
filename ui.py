from pathlib import Path

import streamlit as st

CSS_FILE = Path(__file__).parent / "assets" / "style.css"


def load_css():
    """Inject the custom stylesheet into the page."""
    css = CSS_FILE.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def page_header(title, subtitle=""):
    """Page title with an optional muted subtitle."""
    st.title(title)
    if subtitle:
        st.caption(subtitle)