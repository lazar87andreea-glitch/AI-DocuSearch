"""
GDPR Compliance module for AI DocuSearch.

Provides:
- Consent management
- Data export (right to portability)
- Data deletion (right to erasure)
- Privacy & legal notices
"""

import os
import json
import streamlit as st
from datetime import datetime
from pathlib import Path
from src.cost_tracker import export_cost_data


def get_consent_key() -> str:
    """Get the session state key for consent tracking."""
    return "gdpr_consent_given"


def show_consent_banner() -> bool:
    """
    Show GDPR consent banner on first visit.
    Returns True if user has given consent, False otherwise.
    """
    if get_consent_key() not in st.session_state:
        st.session_state[get_consent_key()] = False
    
    if not st.session_state[get_consent_key()]:
        st.warning("""
        🔒 **Privacy & Data Processing Notice**
        
        By using AI DocuSearch, you consent to:
        - **Processing your documents** with AI models (may be shared with LLM providers)
        - **Storing chat history** for 30 days (auto-deleted after)
        - **Analytics & debugging** via LangSmith for performance monitoring
        - **Language detection** from your IP/browser headers
        
        ✅ **Your rights:**
        - 📥 Download your data anytime
        - 🗑️ Delete your data anytime
        - ⏰ Auto-deletion after 30-90 days
        
        """)

        legal_links = st.container(horizontal=True)
        with legal_links:
            st.page_link(
                "app_pages/privacy_policy.py",
                label="Privacy Policy",
                icon=":material/policy:",
            )
            st.page_link(
                "app_pages/terms_of_service.py",
                label="Terms of Service",
                icon=":material/description:",
            )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ I Agree & Continue", use_container_width=True):
                st.session_state[get_consent_key()] = True
                st.rerun()
        with col2:
            st.info("⚠️ You must consent to use this service", icon="ℹ️")
        
        return False
    
    return True


def export_user_data(session_id: str, history_manager, feedback_manager=None) -> dict:
    """
    Export all user data in GDPR-compliant format (right to data portability).
    
    Args:
        session_id: User's session ID
        history_manager: HistoryManager instance
        feedback_manager: FeedbackManager instance (optional)
    
    Returns:
        dict: User's data in portable JSON format
    """
    data = {
        "export_date": datetime.now().isoformat(),
        "session_id": session_id,
        "version": "1.0",
        "data": {
            "questions_and_answers": [],
            "feedback": [],
            "cost_tracking": {},
            "metadata": {
                "total_questions": 0,
                "total_feedback_entries": 0,
                "export_format": "JSON",
                "portability": "This data can be imported into any compatible service",
            }
        }
    }
    
    # Export cost tracking data
    try:
        cost_data = export_cost_data()
        data["data"]["cost_tracking"] = {
            "total_cost_usd": cost_data.get("total_cost_usd"),
            "remaining_budget_usd": cost_data.get("remaining_budget_usd"),
            "budget_percentage": cost_data.get("budget_percentage"),
            "queries_count": cost_data.get("queries_count"),
            "budget_limit_usd": 0.50,
        }
    except Exception as e:
        print(f"[GDPR] Error exporting cost data: {e}")
    
    # Export chat history
    try:
        if history_manager:
            history = history_manager.load_session_history()
            for entry in history:
                data["data"]["questions_and_answers"].append({
                    "timestamp": entry.get("timestamp"),
                    "question": entry.get("question"),
                    "answer": entry.get("answer"),
                    "document": entry.get("document_name"),
                    "mode": entry.get("mode"),
                    "metrics": entry.get("metrics"),
                })
            data["data"]["metadata"]["total_questions"] = len(history)
    except Exception as e:
        print(f"[GDPR] Error exporting history: {e}")
    
    # Export feedback
    try:
        if feedback_manager:
            feedback = feedback_manager.load_feedback()
            for entry in feedback:
                data["data"]["feedback"].append({
                    "timestamp": entry.get("timestamp"),
                    "rating": entry.get("rating"),
                    "question": entry.get("question"),
                    "type": entry.get("type"),
                    "comment": entry.get("comment"),
                    "document": entry.get("document_name"),
                })
            data["data"]["metadata"]["total_feedback_entries"] = len(feedback)
    except Exception as e:
        print(f"[GDPR] Error exporting feedback: {e}")
    
    return data


def delete_user_data(session_id: str, history_manager, feedback_manager=None) -> bool:
    """
    Delete all user data (right to erasure).
    
    Args:
        session_id: User's session ID
        history_manager: HistoryManager instance
        feedback_manager: FeedbackManager instance (optional)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Delete history
        if history_manager:
            history_file = Path("history") / f"user_{session_id}.json"
            if history_file.exists():
                history_file.unlink()
                print(f"[GDPR] Deleted history for session {session_id}")
        
        # Delete feedback
        if feedback_manager:
            feedback_file = Path("feedback") / f"user_{session_id}.json"
            if feedback_file.exists():
                feedback_file.unlink()
                print(f"[GDPR] Deleted feedback for session {session_id}")
        
        # Clear session state
        st.session_state.chat_history = []
        st.session_state.document_text = None
        st.session_state.rag_pipeline = None
        st.session_state.page_count = None
        
        print(f"[GDPR] All data deleted for session {session_id}")
        return True
    
    except Exception as e:
        print(f"[GDPR] Error deleting user data: {e}")
        return False


def show_gdpr_sidebar(session_id: str, history_manager, feedback_manager=None):
    """
    DEPRECATED: Use show_gdpr_footer instead.
    This function is kept for backwards compatibility.
    """
    pass


def show_gdpr_footer(session_id: str, history_manager, feedback_manager=None):
    """
    Display GDPR compliance links at the bottom of the page (footer).
    
    The footer includes in-app legal pages and controls for:
    - Download data (right to portability)
    - Delete data (right to erasure)
    - Privacy Policy
    - Terms of Service
    - Third-party services
    """
    st.markdown("---")
    st.markdown("### 🔒 Privacy & Data Management")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📥 Download Data", use_container_width=True, help="Export your data (GDPR right to portability)"):
            try:
                user_data = export_user_data(session_id, history_manager, feedback_manager)
                json_str = json.dumps(user_data, indent=2, ensure_ascii=False)
                
                st.download_button(
                    label="💾 Save JSON",
                    data=json_str,
                    file_name=f"docusearch_data_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"download_{session_id}"
                )
                st.success("✅ Your data is ready!")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    with col2:
        show_delete_key = f"show_delete_confirmation_{session_id}"
        confirm_delete_key = f"confirm_delete_{session_id}"

        if st.button("🗑️ Delete Data", use_container_width=True, help="Delete all your data (GDPR right to erasure)"):
            st.session_state[show_delete_key] = True

        if st.session_state.get(show_delete_key, False):
            st.warning("⚠️ This will permanently delete ALL your data!")
            if st.checkbox("I understand - delete everything", key=confirm_delete_key):
                if delete_user_data(session_id, history_manager, feedback_manager):
                    st.session_state[show_delete_key] = False
                    st.success("✅ All data deleted!")
                    st.rerun()
                else:
                    st.error("❌ Error deleting data")
    
    with col3:
        st.page_link(
            "app_pages/privacy_policy.py",
            label="Privacy Policy",
            icon=":material/policy:",
        )
    
    with col4:
        st.page_link(
            "app_pages/terms_of_service.py",
            label="Terms of Service",
            icon=":material/description:",
        )
    
    with col5:
        st.markdown("[🔗 Third Parties](#)")
    
    st.markdown("""
    **Your GDPR Rights:**
    - ✅ Access your data (📥 Download)
    - ✅ Delete your data (🗑️ Delete)
    - ✅ Data portability (JSON format)
    - ✅ Restrict processing
    - ✅ Object to tracking
    """)


def show_third_party_disclosure():
    """
    Show disclosure about third-party data sharing.
    """
    with st.expander("🔗 Third-Party Services"):
        st.markdown("""
        **Your data may be shared with:**
        
        🤖 **LLM Providers** (Process your questions)
        - OpenAI, xAI, Groq, or other configured providers
        - Your questions are sent to their servers
        - Check their privacy policies
        
        🔍 **LangSmith** (Debug & Monitor)
        - Traces your AI interactions for debugging
        - May attach your Helpful/Not helpful rating to the answer trace
        - Detects and logs to https://smith.langchain.com
        - Can be disabled: `LANGSMITH_TRACING=false`
        
        🌐 **Geolocation** (Detect Language)
        - ip-api.com reads your IP for country detection
        - Used only for language selection
        - No personal data required

        📝 **Google Forms** (Optional Testing Feedback)
        - Opens only when you select "Share feedback"
        - Receives the answers you choose to submit and data covered by Google's privacy policy
        - Do not include document content or confidential information
        
        ✅ **We do NOT:**
        - Sell your data
        - Share with advertisers
        - Train models on your documents
        - Use for marketing purposes
        """)


__all__ = [
    "show_consent_banner",
    "export_user_data",
    "delete_user_data",
    "show_gdpr_footer",
    "show_gdpr_sidebar",
    "show_third_party_disclosure",
    "get_consent_key",
]
