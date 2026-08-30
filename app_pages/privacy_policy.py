from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]

navigation = st.container(horizontal=True)
with navigation:
    st.page_link("app_pages/home.py", label="Home", icon=":material/home:")
    st.page_link(
        "app_pages/terms_of_service.py",
        label="Terms of Service",
        icon=":material/description:",
    )

st.markdown((ROOT_DIR / "PRIVACY_POLICY.md").read_text(encoding="utf-8"))