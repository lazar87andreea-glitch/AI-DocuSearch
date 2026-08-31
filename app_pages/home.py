import os
import sys
import time
import re
from uuid import uuid4

# Prevent OpenBLAS/NumPy memory issues on low-memory machines.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import streamlit as st
from dotenv import load_dotenv

from src.history_manager import HistoryManager

load_dotenv()

# Initialize LangSmith with Streamlit's caching model
@st.cache_resource
def _initialize_langsmith():
    """Initialize LangSmith client once per Streamlit session (survives reruns)."""
    def _to_env_string(value):
        """Convert any value to a proper environment variable string."""
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value) if value else ""

    # Load ALL secrets from Streamlit into os.environ (both LLM and LangSmith)
    try:
        if hasattr(st, 'secrets') and st.secrets:
            print(f"[INIT] st.secrets available, loading...", file=sys.stderr)
            # Try direct dict iteration first
            try:
                for key, value in st.secrets.items():
                    converted = _to_env_string(value)
                    os.environ[key] = converted
                    if "LANGSMITH" in key or "LLM" in key:
                        print(f"[INIT] Set {key} (configured)", file=sys.stderr)
            except AttributeError:
                # Fallback for Streamlit secrets that don't support .items()
                print(f"[INIT] st.secrets.items() failed, trying direct access", file=sys.stderr)
                keys_to_check = ["LANGSMITH_API_KEY", "LANGSMITH_TRACING", "LANGSMITH_PROJECT",
                                 "LLM_API_KEY", "LLM_API_BASE", "LLM_MODEL"]
                for key in keys_to_check:
                    try:
                        value = st.secrets.get(key)
                        if value:
                            converted = _to_env_string(value)
                            os.environ[key] = converted
                            print(f"[INIT] Set {key} (configured)", file=sys.stderr)
                    except Exception:
                        pass
        else:
            print(f"[INIT] st.secrets not available or empty", file=sys.stderr)
    except Exception as e:
        print(f"[INIT] Failed to load secrets: {e}", file=sys.stderr)

    # ENSURE LANGSMITH_TRACING is set to "true" (must be string, not boolean)
    if not os.getenv("LANGSMITH_TRACING"):
        print(f"[INIT] WARNING: LANGSMITH_TRACING not set, defaulting to 'true'", file=sys.stderr)
        os.environ["LANGSMITH_TRACING"] = "true"
    else:
        tracing_val = os.getenv("LANGSMITH_TRACING")
        if isinstance(tracing_val, bool):
            # Convert bool to string
            os.environ["LANGSMITH_TRACING"] = "true" if tracing_val else "false"
            print(f"[INIT] Converted LANGSMITH_TRACING to string: {os.environ['LANGSMITH_TRACING']}", file=sys.stderr)

    # Log LangSmith configuration
    print(f"[INIT] LANGSMITH_API_KEY present: {bool(os.getenv('LANGSMITH_API_KEY'))}", file=sys.stderr)
    print(f"[INIT] LANGSMITH_TRACING: '{os.getenv('LANGSMITH_TRACING')}'", file=sys.stderr)
    print(f"[INIT] LANGSMITH_PROJECT: '{os.getenv('LANGSMITH_PROJECT')}'", file=sys.stderr)

    # Now import langsmith with environment properly configured
    try:
        from langsmith import traceable as _langsmith_traceable
        print(f"[INIT] LangSmith imported successfully", file=sys.stderr)
        return _langsmith_traceable
    except Exception as e:
        # Return no-op decorator as fallback
        print(f"[INIT] Failed to import LangSmith: {e}", file=sys.stderr)
        from typing import Callable, TypeVar
        _F = TypeVar("_F", bound=Callable[..., object])

        def _noop_traceable(*_args, **_kwargs):
            def _decorator(fn: _F) -> _F:
                return fn
            return _decorator
        return _noop_traceable

# Initialize LangSmith (cached per session, survives reruns)
traceable = _initialize_langsmith()

# NOW import src modules (they will use traceable decorator with env vars set)
from src.ingest import extract_text, get_pdf_page_count
from src.ai_query import generate_answer_with_meta
from src.pipeline import build_pipeline_from_text, answer_question
from src.upload_storage import cleanup_stale_uploads, temporary_upload
from src.prompt_loader import load_prompt_with_temperature
from src.i18n import translate, get_user_language
from src.gdpr_compliance import show_consent_banner, show_gdpr_footer
from src.cost_tracker import initialize_cost_tracker, get_cost_badge, should_warn, is_blocked, track_query_cost
from src.feedback_manager import FeedbackManager
from src.langsmith_feedback import submit_langsmith_feedback

FEEDBACK_FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSdljvKnBNz8j2y5tMlYPeLgyBa1alR28FRCt393QvFOaoAFuw/viewform"
)

# Initialize LangSmith client for manual tracing
try:
    from langsmith import Client
    _langsmith_client = Client()
    print(f"[INIT] LangSmith Client created: {_langsmith_client}", file=sys.stderr)
except Exception as e:
    print(f"[INIT] Failed to create LangSmith Client: {type(e).__name__}: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    _langsmith_client = None

# Mobile detection helper
def is_mobile_browser():
    """Detect if user is on a mobile device."""
    try:
        user_agent = st.query_params.get("_user_agent", "")
        if not user_agent:
            # Fallback: check if we're in a mobile context
            user_agent = os.environ.get("HTTP_USER_AGENT", "")
        mobile_patterns = r"(android|iphone|ipad|mobile|webos|blackberry|opera mini)"
        return bool(re.search(mobile_patterns, user_agent.lower()))
    except:
        return False

# Verify LangSmith configuration on app startup
@st.cache_resource
def verify_langsmith_config():
    """Cache and verify LangSmith configuration once per app session."""
    api_key = os.environ.get('LANGSMITH_API_KEY')
    tracing = os.environ.get('LANGSMITH_TRACING')
    project = os.environ.get('LANGSMITH_PROJECT')

    is_configured = bool(api_key and tracing == 'true')

    return {
        'api_key_set': bool(api_key),
        'tracing_enabled': tracing == 'true',
        'project': project or 'default',
        'is_configured': is_configured
    }

# Check config on startup (cached, runs once per session)
_langsmith_config = verify_langsmith_config()

# Recover upload files left by an interrupted server process without touching other temp files.
cleanup_stale_uploads()

# Initialize history manager and feedback manager for this session
if "history_manager" not in st.session_state:
    session_id = uuid4().hex
    st.session_state.session_id = session_id  # Store for GDPR access
    st.session_state.history_manager = HistoryManager(session_id)
    st.session_state.feedback_manager = FeedbackManager(session_id)

# Initialize cost tracker for this session
initialize_cost_tracker()

# Run cleanup on every app load (targets old sessions, doesn't affect current one)
history_enabled = os.getenv("HISTORY_ENABLED", "true").lower() in ("true", "1", "yes")
if history_enabled:
    try:
        retention_days = int(os.getenv("HISTORY_RETENTION_DAYS", "30"))
        HistoryManager.cleanup_old_sessions(retention_days=retention_days)
    except Exception:
        pass

# Check if on mobile
is_mobile = is_mobile_browser()

# Show GDPR consent banner (must be accepted to continue)
if not show_consent_banner():
    st.stop()

if is_mobile:
    st.info(
        "📱 **Mobile Device Detected**: Hybrid mode intelligently adapts to your device's capabilities. "
        "It will use fast, efficient processing optimized for mobile."
    )

st.title(translate("title"))
st.markdown(translate("description"))

# Display budget info and cost badge
st.info(translate("budget_info"))
budget_blocked = is_blocked()
col1, col2 = st.columns([3, 1])
with col1:
    if not budget_blocked:
        st.link_button(
            "Share feedback",
            FEEDBACK_FORM_URL,
            icon=":material/rate_review:",
            help="Open the AI DocuSearch testing feedback form in a new tab.",
        )
with col2:
    st.markdown(get_cost_badge())

# Show warning if approaching budget limit
if should_warn() and not budget_blocked:
    st.warning(
        "**Free testing trial nearly complete:** You are approaching the trial limit. "
        "Only a small amount of usage remains."
    )

# Show blocking message if budget exceeded
if budget_blocked:
    st.error(
        "**Free testing trial complete:** Your free testing trial has ended. "
        "Please share your experience using the form below. Your feedback will help improve "
        "AI DocuSearch and is greatly appreciated."
    )
    st.link_button(
        "Share feedback",
        FEEDBACK_FORM_URL,
        type="primary",
        icon=":material/rate_review:",
        help="Open the AI DocuSearch testing feedback form in a new tab.",
    )
    st.stop()


@traceable(run_type="chain", name="web_app.rag_mode")
def run_rag(pipeline: dict, question: str, document_info: str = "Unknown") -> dict:
    result = answer_question(pipeline, question, document_info=document_info)
    result["build_seconds"] = 0.0
    result["fallback_reason"] = None
    result["mode"] = "RAG"
    return result


@traceable(run_type="chain", name="web_app.direct_llm_mode")
def run_direct(document_text: str, question: str, document_info: str = "Unknown") -> dict:
    prompt, temperature = load_prompt_with_temperature("direct_llm_prompt", document_text=document_text, question=question, document_info=document_info)
    meta = generate_answer_with_meta(prompt, temperature=temperature)
    return {
        "query": question,
        "raw_answer": meta["answer"],
        "response_status": meta["response_status"],
        "error_type": meta["error_type"],
        "error_message": meta["error_message"],
        "source_chunks": [],
        "lite_mode": True,
        "build_seconds": 0.0,
        "retrieval_seconds": 0.0,
        "generation_seconds": meta["elapsed_seconds"],
        "total_seconds": meta["elapsed_seconds"],
        "chunk_count": 0,
        "context_chars": len(document_text),
        "prompt_tokens": meta["prompt_tokens"],
        "completion_tokens": meta["completion_tokens"],
        "total_tokens": meta["total_tokens"],
        "estimated_tokens": meta["estimated_tokens"],
        "used_live_api": meta["used_live_api"],
        "langsmith_run_id": meta["langsmith_run_id"],
        "temperature": meta["temperature"],
        "fallback_reason": None,
        "requested_pdf_pages": [],
    }


def _is_rag_inconclusive(answer: str) -> bool:
    """Check if RAG returned an 'I don't know' or similar inconclusive answer."""
    answer_lower = answer.lower().strip()
    inconclusive_patterns = [
        # English patterns
        "does not provide",
        "does not contain",
        "do not contain",
        "not found in",
        "cannot find",
        "i don't know",
        "i do not know",
        "unclear",
        "not specified",
        "not mentioned",
        # Romanian patterns
        "nu furnizeaza",
        "nu oferă",
        "nu contine",
        "nu am gasit",
        "nu este mentionat",
        "nu se specifica",
        # French patterns
        "ne fournit pas",
        "ne contient pas",
        "non trouvé",
        "n'a pas trouvé",
        "ne contient aucune",
        "pas spécifié",
        # Spanish patterns
        "no proporciona",
        "no contiene",
        "no encontrado",
        "no encontré",
        "no se especifica",
        "no menciona",
        # German patterns
        "liefert nicht",
        "enthält nicht",
        "nicht gefunden",
        "nicht gefunden",
        "nicht angegeben",
        "nicht erwähnt",
    ]
    return any(pattern in answer_lower for pattern in inconclusive_patterns)


@traceable(run_type="chain", name="web_app.hybrid_mode")
def run_hybrid(pipeline: dict | None, document_text: str, question: str, document_info: str = "Unknown") -> dict:
    print(f"[HYBRID] Starting Hybrid mode for question: {question[:50]}...", file=sys.stderr)
    if pipeline is None:
        fallback_result = run_direct(document_text, question, document_info=document_info)
        fallback_result["fallback_reason"] = "RAG pipeline unavailable"
        fallback_result["mode"] = "Hybrid (fallback to DirectLLM)"
        return fallback_result

    try:
        print(f"[HYBRID] Attempting RAG pipeline...", file=sys.stderr)
        result = run_rag(pipeline, question, document_info=document_info)
        if result.get("response_status", "success") != "success":
            result["mode"] = "Hybrid (RAG)"
            return result

        answer_text = result.get('raw_answer', '')
        print(f"[HYBRID] RAG succeeded, answer length: {len(answer_text)} chars", file=sys.stderr)

        # Check if RAG returned an inconclusive answer
        if not result.get("requested_pdf_pages") and _is_rag_inconclusive(answer_text):
            print(f"[HYBRID] RAG returned inconclusive answer. Trying Direct LLM for better results...", file=sys.stderr)
            fallback_result = run_direct(document_text, question, document_info=document_info)
            fallback_result["fallback_reason"] = "RAG found insufficient information in document"
            fallback_result["mode"] = "Hybrid (fallback to DirectLLM)"
            print(f"[HYBRID] Direct LLM fallback succeeded, answer length: {len(fallback_result.get('raw_answer', ''))} chars", file=sys.stderr)
            return fallback_result

        result["mode"] = "Hybrid (RAG)"
        return result
    except Exception as e:
        print(f"[HYBRID] RAG failed: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(f"[HYBRID] Falling back to Direct LLM mode...", file=sys.stderr)
        result = run_direct(document_text, question, document_info=document_info)
        result["fallback_reason"] = f"{type(e).__name__}: {e}"
        result["mode"] = "Hybrid (fallback to DirectLLM)"
        print(f"[HYBRID] Direct LLM fallback succeeded, answer length: {len(result.get('raw_answer', ''))} chars", file=sys.stderr)
        return result


def render_metrics(result: dict):
    """Render metrics with responsive layout (2 cols on mobile, 4 on desktop)."""
    num_cols = 2 if is_mobile else 4
    cols = st.columns(num_cols)
    cols[0].metric("Total time", f"{result['total_seconds']:.2f}s")
    cols[1].metric("Chunks used", result["chunk_count"])
    if num_cols == 4:
        cols[2].metric("Context size", f"{result['context_chars']:,} chars")
        tok_label = "Tokens (est.)" if result["estimated_tokens"] else "Tokens (actual)"
        cols[3].metric(tok_label, f"{result['total_tokens']:,}")
    else:
        # On mobile, show in second row
        cols[0].metric("Context size", f"{result['context_chars']:,} chars")
        tok_label = "Tokens (est.)" if result["estimated_tokens"] else "Tokens (actual)"
        cols[1].metric(tok_label, f"{result['total_tokens']:,}")

    with st.expander("Detailed timing & tokens"):
        st.write(f"- Build/index time: {result['build_seconds']:.2f}s")
        st.write(f"- Retrieval time: {result['retrieval_seconds']:.2f}s")
        st.write(f"- Generation time: {result['generation_seconds']:.2f}s")
        st.write(f"- Temperature: {result['temperature']}")
        st.write(f"- Prompt tokens: {result['prompt_tokens']:,}")
        st.write(f"- Completion tokens: {result['completion_tokens']:,}")
        st.write(f"- Live API used: {'Yes' if result['used_live_api'] else 'No (simulated fallback)'}")
        if result["lite_mode"]:
            reason = result.get("fallback_reason")
            st.write(f"- ⚠ Ran in lite/keyword-search mode{f' (fallback cause: {reason})' if reason else ''}")


def render_feedback(answer_id: str, question: str, result: dict) -> None:
    """Render feedback buttons (thumbs up/down) for the answer."""
    st.markdown("---")
    st.markdown("**👍 Was this answer helpful?**")

    col1, col2, col3 = st.columns([1, 1, 3])

    feedback_manager = st.session_state.get("feedback_manager")
    document_name = st.session_state.get("uploaded_name", "unknown")

    with col1:
        if st.button("👍 Helpful", key=f"feedback_positive_{answer_id}"):
            feedback_manager.add_feedback(
                answer_id=answer_id,
                rating=True,
                question=question,
                document_name=document_name,
                comment="",
                feedback_type="answer_rating",
                mode=result.get("mode", "Hybrid"),
                answer_length=len(str(result.get("raw_answer", ""))),
                chunk_count=result.get("chunk_count", 0),
                retrieval_seconds=result.get("retrieval_seconds", 0),
                langsmith_run_id=result.get("langsmith_run_id"),
            )
            submit_langsmith_feedback(result.get("langsmith_run_id"), True)
            st.success("✅ Thanks for the feedback!")
            print(f"[FEEDBACK] Positive feedback for {answer_id}", file=sys.stderr)

    with col2:
        if st.button("👎 Not helpful", key=f"feedback_negative_{answer_id}"):
            feedback_manager.add_feedback(
                answer_id=answer_id,
                rating=False,
                question=question,
                document_name=document_name,
                comment="",
                feedback_type="answer_rating",
                mode=result.get("mode", "Hybrid"),
                answer_length=len(str(result.get("raw_answer", ""))),
                chunk_count=result.get("chunk_count", 0),
                retrieval_seconds=result.get("retrieval_seconds", 0),
                langsmith_run_id=result.get("langsmith_run_id"),
            )
            submit_langsmith_feedback(result.get("langsmith_run_id"), False)
            st.warning("📝 We'll use this to improve!")
            print(f"[FEEDBACK] Negative feedback for {answer_id}", file=sys.stderr)


def render_result(mode_key: str, result: dict):
    """Show the answer, feedback buttons, then a toggle button that reveals metrics on demand."""
    st.subheader("Answer")
    st.write(result["raw_answer"])

    # Render feedback buttons
    answer_id = f"ans_{int(time.time() * 1000)}_{mode_key}"
    render_feedback(answer_id, st.session_state.get("last_question", ""), result)

    show_flag = f"show_metrics_{mode_key}"
    if show_flag not in st.session_state:
        st.session_state[show_flag] = False

    label = "📊 Hide metrics" if st.session_state[show_flag] else "📊 Show metrics"
    if st.button(label, key=f"toggle_{show_flag}"):
        st.session_state[show_flag] = not st.session_state[show_flag]

    if st.session_state[show_flag]:
        render_metrics(result)


def log_to_history(mode: str, question: str, result: dict, document_name: str) -> None:
    """Log a query to history both in-memory and to disk."""
    print(f"[HISTORY] log_to_history called: mode={mode}, history_enabled={history_enabled}", file=sys.stderr)

    if not history_enabled:
        print(f"[HISTORY] History disabled, skipping", file=sys.stderr)
        return

    if not st.session_state.history_manager:
        print(f"[HISTORY] history_manager not initialized, skipping", file=sys.stderr)
        return

    try:
        # Extract answer and validate
        answer = result.get("raw_answer", "")
        print(f"[HISTORY] Extracted answer length: {len(answer)} chars, type: {type(answer)}", file=sys.stderr)
        if not answer or answer.strip() == "":
            print(f"[HISTORY] WARNING: Answer is empty!", file=sys.stderr)

        # Extract metrics from result
        metrics_dict = {
            "total_seconds": result.get("total_seconds", 0),
            "retrieval_seconds": result.get("retrieval_seconds", 0),
            "generation_seconds": result.get("generation_seconds", 0),
            "chunk_count": result.get("chunk_count", 0),
            "prompt_tokens": result.get("prompt_tokens", 0),
            "completion_tokens": result.get("completion_tokens", 0),
            "total_tokens": result.get("total_tokens", 0),
            "temperature": result.get("temperature", 0.2),
            "langsmith_run_id": result.get("langsmith_run_id"),
        }

        # Create history entry with timestamp
        from datetime import datetime
        entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer,
            "mode": mode,
            "document_name": document_name,
            "metrics": metrics_dict,
        }

        print(f"[HISTORY] Created entry with document_name={document_name}", file=sys.stderr)

        # Add to in-memory session state (for instant display in chat)
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        st.session_state.chat_history.append(entry)
        print(f"[HISTORY] Added to session state: {len(st.session_state.chat_history)} entries total", file=sys.stderr)
        print(f"[HISTORY] Current chat_history document_names: {[e.get('document_name') for e in st.session_state.chat_history]}", file=sys.stderr)

        # Log to disk history (for analytics/CLI)
        st.session_state.history_manager.add_question(
            question=question,
            answer=answer,
            mode=mode,
            metrics_dict=metrics_dict,
            document_name=document_name
        )
        print(f"[HISTORY] Successfully logged question to disk", file=sys.stderr)
    except Exception as e:
        print(f"[HISTORY] Failed to log question: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)


def render_history_sidebar() -> None:
    """Sidebar is empty - GDPR features moved to footer, auto language detection handles i18n."""
    pass


def render_chat_history() -> None:
    """Display conversation history from in-memory session state with left/right aligned bubbles."""
    # Use session state first (always available in current session)
    if "chat_history" not in st.session_state or not st.session_state.chat_history:
        print("[RENDER] No chat_history entries to display", file=sys.stderr)
        return

    # Get current document filter
    current_doc = st.session_state.get("uploaded_name", None)
    print(f"[RENDER] Rendering chat history for document: {current_doc}", file=sys.stderr)
    print(f"[RENDER] Total entries in chat_history: {len(st.session_state.chat_history)}", file=sys.stderr)

    # Filter history by current document if needed
    recent = [
        entry for entry in st.session_state.chat_history
        if entry.get("document_name") == current_doc
    ]

    print(f"[RENDER] Filtered to {len(recent)} entries for current document", file=sys.stderr)

    if not recent:
        print("[RENDER] No entries for current document, checking document names in history:", file=sys.stderr)
        for entry in st.session_state.chat_history:
            doc_name = entry.get('document_name')
            print(f"[RENDER]   - {doc_name}", file=sys.stderr)
        return

    print(f"[RENDER] Rendering {len(recent)} entries", file=sys.stderr)

    # Chat styling with left/right aligned bubbles and avatars
    st.markdown("""
    <style>
        .chat-message {
            display: flex;
            margin-bottom: 16px;
            align-items: flex-start;
            gap: 8px;
        }
        .chat-message.user {
            justify-content: flex-start;
        }
        .chat-message.bot {
            justify-content: flex-end;
        }
        .chat-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: white;
            font-size: 12px;
            flex-shrink: 0;
            line-height: 1;
        }
        .chat-avatar.user {
            background-color: #4caf50;
            order: -1;
        }
        .chat-avatar.bot {
            background-color: #2196f3;
        }
        .chat-bubble {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 12px;
            word-wrap: break-word;
            color: #000;
        }
        .chat-bubble.user {
            background-color: #d3d3d3;
        }
        .chat-bubble.bot {
            background-color: #4caf50;
            color: white;
        }
        .chat-info {
            font-size: 0.75em;
            margin-top: 4px;
        }
        .chat-info.user {
            color: #666;
        }
        .chat-info.bot {
            color: rgba(255,255,255,0.8);
        }
        @media (prefers-color-scheme: dark) {
            .chat-bubble.user {
                background-color: #555;
                color: #fff;
            }
            .chat-bubble.bot {
                background-color: #2e7d32;
                color: white;
            }
            .chat-info.user {
                color: #aaa;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    # Display each conversation turn
    for entry in reversed(recent):
        # Format timestamp to HH:MM instead of ISO format (2026-08-25T14:36 -> 14:36)
        try:
            iso_timestamp = entry.get("timestamp", "")
            if "T" in iso_timestamp:
                time_part = iso_timestamp.split("T")[1][:5]  # Extract HH:MM from ISO format
            else:
                time_part = iso_timestamp[:16]
        except:
            time_part = entry.get("timestamp", "")[:16]

        mode = entry.get("mode", "")
        question = entry.get("question", "")
        answer = entry.get("answer", "")
        metrics = entry.get("metrics", {})

        # User message (left-aligned)
        st.markdown(f"""
        <div class="chat-message user">
            <div class="chat-avatar user">YOU</div>
            <div>
                <div class="chat-bubble user">{question}</div>
                <div class="chat-info user">{time_part}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Bot message (right-aligned)
        st.markdown(f"""
        <div class="chat-message bot">
            <div>
                <div class="chat-bubble bot">{answer}</div>
            </div>
            <div class="chat-avatar bot">BOT</div>
        </div>
        """, unsafe_allow_html=True)

        # Feedback buttons for this answer
        col1, col2, col3 = st.columns([1, 1, 3])
        feedback_manager = st.session_state.get("feedback_manager")
        document_name = st.session_state.get("uploaded_name", "unknown")
        answer_id = f"ans_{entry.get('timestamp', '')}"

        with col1:
            if st.button("👍 Helpful", key=f"feedback_positive_{answer_id}"):
                if feedback_manager:
                    feedback_manager.add_feedback(
                        answer_id=answer_id,
                        rating=True,
                        question=question,
                        document_name=document_name,
                        comment="",
                        feedback_type="answer_rating",
                        mode=mode,
                        answer_length=len(str(answer)),
                        chunk_count=metrics.get("chunk_count", 0),
                        retrieval_seconds=metrics.get("retrieval_seconds", 0),
                        langsmith_run_id=metrics.get("langsmith_run_id"),
                    )
                    submit_langsmith_feedback(metrics.get("langsmith_run_id"), True)
                    st.success("✅ Thanks for the feedback!")
                    print(f"[FEEDBACK] Positive feedback for {answer_id}", file=sys.stderr)

        with col2:
            if st.button("👎 Not helpful", key=f"feedback_negative_{answer_id}"):
                if feedback_manager:
                    feedback_manager.add_feedback(
                        answer_id=answer_id,
                        rating=False,
                        question=question,
                        document_name=document_name,
                        comment="",
                        feedback_type="answer_rating",
                        mode=mode,
                        answer_length=len(str(answer)),
                        chunk_count=metrics.get("chunk_count", 0),
                        retrieval_seconds=metrics.get("retrieval_seconds", 0),
                        langsmith_run_id=metrics.get("langsmith_run_id"),
                    )
                    submit_langsmith_feedback(metrics.get("langsmith_run_id"), False)
                    st.warning("📝 We'll use this to improve!")
                    print(f"[FEEDBACK] Negative feedback for {answer_id}", file=sys.stderr)

        st.markdown("---")


def render_aggregate_metrics() -> None:
    """Display aggregate metrics for all questions at the bottom."""
    if not history_enabled or not st.session_state.history_manager:
        return

    current_doc = st.session_state.get("uploaded_name", None)
    if not current_doc:
        return

    # Get all questions for this document
    history_limit = int(os.getenv("HISTORY_LIMIT", "10"))
    recent = st.session_state.history_manager.get_recent_questions(
        document_name=current_doc,
        limit=history_limit
    )

    if not recent:
        return

    # Calculate aggregate metrics
    total_time = sum(e.get('metrics', {}).get('total_seconds', 0) for e in recent)
    total_tokens = sum(e.get('metrics', {}).get('total_tokens', 0) for e in recent)
    total_prompt_tokens = sum(e.get('metrics', {}).get('prompt_tokens', 0) for e in recent)
    total_completion_tokens = sum(e.get('metrics', {}).get('completion_tokens', 0) for e in recent)
    avg_time = total_time / len(recent) if recent else 0

    # Mode breakdown
    mode_counts = {}
    for entry in recent:
        mode = entry.get('mode', 'Unknown')
        mode_counts[mode] = mode_counts.get(mode, 0) + 1

    st.markdown("---")
    st.markdown("### 📊 Session Metrics")

    # Main metrics in 4 columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Queries", len(recent))
    with col2:
        st.metric("Total Response Time", f"{total_time:.2f}s")
    with col3:
        st.metric("Avg Response Time", f"{avg_time:.2f}s")
    with col4:
        st.metric("Total Tokens", total_tokens)

    # Token breakdown
    col5, col6, col7 = st.columns(3)
    with col5:
        st.metric("Prompt Tokens", total_prompt_tokens)
    with col6:
        st.metric("Completion Tokens", total_completion_tokens)
    with col7:
        modes_str = ", ".join([f"{mode}({count})" for mode, count in mode_counts.items()])
        st.metric("Modes Used", modes_str, label_visibility="visible")


if "document_text" not in st.session_state:
    st.session_state.document_text = None
if "rag_pipeline" not in st.session_state:
    st.session_state.rag_pipeline = None
if "page_count" not in st.session_state:
    st.session_state.page_count = None
if "extraction_seconds" not in st.session_state:
    st.session_state.extraction_seconds = None
if "results" not in st.session_state:
    st.session_state.results = {}
if "last_question" not in st.session_state:
    st.session_state.last_question = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "loaded_docs" not in st.session_state:
    st.session_state.loaded_docs = set()

uploaded = st.file_uploader(translate("upload_prompt"), type=["pdf", "docx", "txt"])

if uploaded is not None:
    if st.session_state.get("uploaded_name") != uploaded.name:
        st.session_state.uploaded_name = uploaded.name
        st.session_state.results = {}
        st.session_state.document_text = None
        st.session_state.rag_pipeline = None
        st.session_state.page_count = None

        # Extract while the temporary upload exists; the context always removes it.
        try:
            with temporary_upload(uploaded.name, uploaded.getbuffer()) as file_path:
                st.info(f"{translate('file_saved')}: {uploaded.name} ({uploaded.size} bytes)")
                st.info(translate("extracting"))
                t0 = time.perf_counter()
                document_text = extract_text(file_path)
                extraction_seconds = time.perf_counter() - t0
                page_count = (
                    get_pdf_page_count(file_path)
                    if file_path.lower().endswith(".pdf")
                    else None
                )

            st.session_state.document_text = document_text
            st.session_state.extraction_seconds = extraction_seconds
            st.session_state.page_count = page_count

            try:
                st.session_state.rag_pipeline = build_pipeline_from_text(
                    document_text,
                    use_embeddings=True,
                )
            except Exception as pipeline_error:
                st.session_state.rag_pipeline = None
                print(
                    f"[WARNING] RAG pipeline unavailable; Direct LLM fallback will be used: "
                    f"{type(pipeline_error).__name__}: {pipeline_error}",
                    file=sys.stderr,
                )

            size_mb = len(document_text) / (1024 * 1024)
            page_info = ""
            if page_count:
                page_info = f", {page_count} {translate('pages')}"

            st.success(
                f"{translate('extracted')} {len(document_text)} {translate('chars')} "
                f"({size_mb:.2f} {translate('mb')}){page_info} "
                f"{translate('in')} {extraction_seconds:.2f}{translate('seconds')}"
            )

            # Load existing history for this document into session state (one-time per upload)
            if history_enabled and st.session_state.history_manager:
                try:
                    doc_name = st.session_state.get("uploaded_name")
                    if doc_name and doc_name not in st.session_state.loaded_docs:
                        disk_history = st.session_state.history_manager.get_recent_questions(
                            document_name=doc_name,
                            limit=int(os.getenv("HISTORY_LIMIT", "10"))
                        )
                        if disk_history:
                            # Prepend disk history to session state (oldest first)
                            st.session_state.chat_history = disk_history + st.session_state.chat_history
                            st.session_state.loaded_docs.add(doc_name)
                            print(f"[HISTORY] Loaded {len(disk_history)} entries from disk for {doc_name}", file=sys.stderr)
                except Exception as e:
                    print(f"[HISTORY] Failed to load disk history: {e}", file=sys.stderr)

        except RuntimeError as e:
            # OCR-related errors
            st.warning(f"⚠️ **Note on scanned PDFs**: {e}")
            st.info("📌 **Tip**: For best results, use PDFs with selectable text (not scanned images). "
                    "If you have a scanned PDF in a non-English language, OCR may need configuration.")
            st.session_state.document_text = None
            st.session_state.rag_pipeline = None
            st.session_state.page_count = None
            print(f"[WARNING] Text extraction (OCR): {e}", file=sys.stderr)
        except Exception as e:
            st.error(f"{translate('failed_extract')}: {type(e).__name__}: {e}")
            st.session_state.document_text = None
            st.session_state.rag_pipeline = None
            st.session_state.page_count = None
            print(f"[ERROR] Text extraction failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
else:
    # No file uploaded yet - show helpful message
    if "uploaded_name" not in st.session_state:
        st.info(translate("upload_first"))

# Render history sidebar
render_history_sidebar()

# Initialize chat history for conversation
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# If document is uploaded, show chat interface
if st.session_state.document_text:
    # Hybrid mode is the only mode
    mode = "Hybrid"

    st.markdown("---")

    # Show conversation history
    render_chat_history()

    st.markdown("---")

    # Chat input
    question = st.chat_input(translate("ask_question") + " 📝", key="chat_input")

    if question:
        # Store question for feedback
        st.session_state.last_question = question

        # Show processing message
        with st.spinner(translate("processing")):
            try:
                print(f"[CHAT] Processing question with Hybrid mode", file=sys.stderr)
                print(f"[CHAT] uploaded_name: {st.session_state.get('uploaded_name')}", file=sys.stderr)

                # Prepare document info for the LLM
                document_info_parts = []
                if st.session_state.get("uploaded_name"):
                    document_info_parts.append(f"Document: {st.session_state.get('uploaded_name')}")
                if st.session_state.get("page_count"):
                    document_info_parts.append(f"Pages: {st.session_state.get('page_count')}")
                document_info = " | ".join(document_info_parts) if document_info_parts else "Unknown"

                # Always use Hybrid mode (tries RAG, falls back to Direct LLM if needed)
                print(f"[CHAT] Running Hybrid mode", file=sys.stderr)
                result = run_hybrid(
                    st.session_state.rag_pipeline,
                    st.session_state.document_text,
                    question,
                    document_info=document_info,
                )

                print(f"[CHAT] Got result with keys: {list(result.keys())}", file=sys.stderr)
                print(f"[CHAT] Result raw_answer length: {len(result.get('raw_answer', ''))} chars", file=sys.stderr)

                response_status = result.get("response_status", "success")
                if response_status == "success":
                    # Track cost only when the provider returned a real answer.
                    prompt_tokens = result.get("prompt_tokens", 0)
                    completion_tokens = result.get("completion_tokens", 0)
                    track_query_cost(prompt_tokens, completion_tokens)
                    print(f"[COST] Tracked query cost: {prompt_tokens} input + {completion_tokens} output tokens", file=sys.stderr)

                    # Log only successful answers to history.
                    print(f"[CHAT] Calling log_to_history...", file=sys.stderr)
                    log_to_history(mode, question, result, st.session_state.get("uploaded_name", "unknown"))
                    print(f"[CHAT] log_to_history completed", file=sys.stderr)

                    # Rerun to update chat history display with feedback buttons
                    st.rerun()
                elif response_status == "simulated":
                    st.warning(
                        "The language model is not configured. This simulated preview was not "
                        "saved to history or counted toward your usage."
                    )
                    st.write(result.get("raw_answer", ""))
                else:
                    st.error(
                        "The language model provider could not complete this request. "
                        "No answer was saved and the request was not counted toward this app's "
                        "usage budget."
                    )
                    st.info("Please try again later or contact the application operator if the problem continues.")

            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                st.error(f"❌ **Error**: {error_msg}")
                st.info("**Troubleshooting:**\n- Check your API key in Streamlit secrets\n- Try with a smaller document\n- Check the Streamlit Cloud logs for details")
                print(f"[ERROR] {mode} failed: {error_msg}", file=sys.stderr)
                import traceback
                traceback.print_exc()

else:
    # No document uploaded yet
    question = None
    can_run = False

# Display GDPR footer at the bottom of every page
show_gdpr_footer(
    session_id=str(st.session_state.get("session_id", "unknown")),
    history_manager=st.session_state.get("history_manager"),
    feedback_manager=st.session_state.get("feedback_manager")
)
