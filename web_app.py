import streamlit as st


st.set_page_config(page_title="AI DocuSearch", layout="wide")

page = st.navigation(
    [
        st.Page(
            "app_pages/home.py",
            title="AI DocuSearch",
            icon=":material/search:",
            default=True,
        ),
        st.Page(
            "app_pages/privacy_policy.py",
            title="Privacy Policy",
            icon=":material/policy:",
        ),
        st.Page(
            "app_pages/terms_of_service.py",
            title="Terms of Service",
            icon=":material/description:",
        ),
        st.Page(
            "app_pages/third_party_services.py",
            title="Third-Party Services",
            icon=":material/handshake:",
        ),
    ],
    position="hidden",
)

page.run()
