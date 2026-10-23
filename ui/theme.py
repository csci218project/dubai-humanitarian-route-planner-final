"""Load the Victorian chart-room stylesheet into the page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

CSS_PATH = Path(__file__).with_name("theme.css")


def inject_theme() -> None:
    """Add ui/theme.css to the page.

    Passing a Path to a .css file makes Streamlit wrap it in <style> tags and
    place it outside the layout, so it takes up no space.
    """
    st.html(CSS_PATH)
