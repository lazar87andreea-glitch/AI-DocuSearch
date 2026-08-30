from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]

navigation = st.container(horizontal=True)
with navigation:
    st.page_link("app_pages/home.py", label="Home", icon=":material/home:")
    st.page_link(
        "app_pages/privacy_policy.py",
        label="Privacy Policy",
        icon=":material/policy:",
    )

st.markdown((ROOT_DIR / "TERMS_OF_SERVICE.md").read_text(encoding="utf-8"))