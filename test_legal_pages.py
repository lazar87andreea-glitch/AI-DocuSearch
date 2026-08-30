"""Streamlit navigation tests for the legal document pages."""

from streamlit.testing.v1 import AppTest


def test_legal_page_navigation() -> None:
    app = AppTest.from_file("web_app.py", default_timeout=30)
    app.session_state["gdpr_consent_given"] = True
    app.run()

    link_labels = [link.label for link in app.get("page_link")]
    assert "Privacy Policy" in link_labels
    assert "Terms of Service" in link_labels

    app.switch_page("app_pages/privacy_policy.py").run()
    assert not app.exception
    assert any(
        "Privacy Policy for AI DocuSearch" in item.value for item in app.markdown
    )

    app.switch_page("app_pages/terms_of_service.py").run()
    assert not app.exception
    assert any(
        "Terms of Service for AI DocuSearch" in item.value for item in app.markdown
    )


if __name__ == "__main__":
    test_legal_page_navigation()
    print("Legal page navigation test passed.")