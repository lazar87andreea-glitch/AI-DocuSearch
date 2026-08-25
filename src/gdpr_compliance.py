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
        
        📋 See [Privacy Policy](PRIVACY_POLICY.md) | [Terms of Service](TERMS_OF_SERVICE.md)
        """)
        
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
            "metadata": {
                "total_questions": 0,
                "total_feedback_entries": 0,
                "export_format": "JSON",
                "portability": "This data can be imported into any compatible service",
            }
        }
    }
    
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
        st.session_state.file_path = None
        st.session_state.page_count = None
        
        print(f"[GDPR] All data deleted for session {session_id}")
        return True
    
    except Exception as e:
        print(f"[GDPR] Error deleting user data: {e}")
        return False


def show_gdpr_sidebar(session_id: str, history_manager, feedback_manager=None):
    """
    Display GDPR compliance options in the sidebar.
    
    Provides:
    - Download my data (right to portability)
    - Delete my data (right to erasure)
    - Privacy policy & terms links
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔒 **Privacy & Data**")
    
    # Data Export
    with st.sidebar.expander("📥 Download My Data"):
        st.write("Export all your personal data (GDPR right to data portability)")
        st.info(
            "This includes:\n"
            "- All your questions and answers\n"
            "- Feedback and ratings\n"
            "- Session metadata\n"
            "- Format: JSON (portable)"
        )
        
        if st.button("📥 Export as JSON", use_container_width=True, key="export_data"):
            try:
                user_data = export_user_data(session_id, history_manager, feedback_manager)
                json_str = json.dumps(user_data, indent=2, ensure_ascii=False)
                
                st.download_button(
                    label="💾 Download JSON File",
                    data=json_str,
                    file_name=f"docusearch_data_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
                st.success("✅ Your data is ready to download!")
            except Exception as e:
                st.error(f"❌ Error exporting data: {e}")
    
    # Data Deletion
    with st.sidebar.expander("🗑️ Delete My Data"):
        st.write("Permanently delete all your data (GDPR right to erasure)")
        st.warning(
            "⚠️ **This action is irreversible!**\n\n"
            "This will delete:\n"
            "- All questions and answers\n"
            "- All feedback and ratings\n"
            "- All session history\n"
            "- All metadata"
        )
        
        if st.button("🗑️ Delete ALL My Data", use_container_width=True, key="delete_data"):
            if st.checkbox("I understand this is permanent and irreversible"):
                if delete_user_data(session_id, history_manager, feedback_manager):
                    st.success("✅ All your data has been permanently deleted!")
                    st.info("You can now upload a new document and start fresh.")
                    st.rerun()
                else:
                    st.error("❌ Error deleting data. Please try again.")
    
    # Legal Documents
    with st.sidebar.expander("📋 Legal Documents"):
        st.write("View our legal policies:")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("[📜 Privacy Policy](PRIVACY_POLICY.md)")
        with col2:
            st.markdown("[📜 Terms of Service](TERMS_OF_SERVICE.md)")
        
        st.markdown("---")
        st.write("**Your Rights under GDPR:**")
        st.markdown("""
        - ✅ Right to Access - Download your data
        - ✅ Right to Erasure - Delete your data
        - ✅ Right to Data Portability - Get data in portable format
        - ✅ Right to Restrict Processing - Contact us
        - ✅ Right to Object - Opt out of tracking
        
        **Questions?** Contact: [your-email] or [GitHub link]
        """)


def show_third_party_disclosure():
    """
    Show disclosure about third-party data sharing.
    """
    with st.sidebar.expander("🔗 Third-Party Services"):
        st.markdown("""
        **Your data may be shared with:**
        
        🤖 **LLM Providers** (Process your questions)
        - OpenAI, xAI, Groq, or other configured providers
        - Your questions are sent to their servers
        - Check their privacy policies
        
        🔍 **LangSmith** (Debug & Monitor)
        - Traces your AI interactions for debugging
        - Detects and logs to https://smith.langchain.com
        - Can be disabled: `LANGSMITH_TRACING=false`
        
        🌐 **Geolocation** (Detect Language)
        - ip-api.com reads your IP for country detection
        - Used only for language selection
        - No personal data required
        
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
    "show_gdpr_sidebar",
    "show_third_party_disclosure",
    "get_consent_key",
]
