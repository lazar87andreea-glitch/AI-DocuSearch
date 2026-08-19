import os
import sys
import tempfile
import time
import re

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
        if hasattr(st, 'secrets'):
            for key, value in st.secrets.items():
                converted = _to_env_string(value)
                os.environ[key] = converted
    except Exception:
        pass
    
    # Now import langsmith with environment properly configured
    try:
        from langsmith import traceable as _langsmith_traceable
        return _langsmith_traceable
    except Exception:
        # Return no-op decorator as fallback
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
from src.ingest import extract_text
from src.ai_query import generate_answer_with_meta
from src.pipeline import build_pipeline, answer_question
from src.prompt_loader import load_prompt_with_temperature

# Initialize LangSmith client for manual tracing
try:
    from langsmith import Client
    _langsmith_client = Client()
except Exception:
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

st.set_page_config(page_title="DocuSearch", layout="wide")

# Initialize history manager for this session
if "history_manager" not in st.session_state:
    session_id = str(hash((st.session_state.session_id if hasattr(st.session_state, 'session_id') else id(st.session_state))) % (10 ** 8))
    st.session_state.history_manager = HistoryManager(session_id)

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

if is_mobile:
    st.warning(
        "📱 **Mobile Mode Active**: RAG & Hybrid modes disabled. Use **Direct LLM** mode instead — "
        "it's fast and works on all devices!"
    )

st.title("DocuSearch")
st.markdown(
    "Don't remember what a document is all about? Click Upload button, wait to load, ask a question "
    "then run in it one or all the options below to see the response. Metrics (speed, retrieval, token usage) are optional — click Show metrics under any answer to reveal them"
)


def save_uploaded(uploaded_file):
    suffix = os.path.splitext(uploaded_file.name)[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getbuffer())
    tmp.flush()
    tmp.close()
    return tmp.name


@traceable(run_type="chain", name="web_app.rag_mode")
def run_rag(file_path: str, question: str) -> dict:
    t0 = time.perf_counter()
    pipeline = build_pipeline(file_path, use_embeddings=True)
    build_seconds = time.perf_counter() - t0
    result = answer_question(pipeline, question)
    result["build_seconds"] = build_seconds
    result["total_seconds"] += build_seconds
    result["fallback_reason"] = None
    return result


@traceable(run_type="chain", name="web_app.direct_llm_mode")
def run_direct(document_text: str, question: str) -> dict:
    prompt, temperature = load_prompt_with_temperature("direct_llm_prompt", document_text=document_text, question=question)
    meta = generate_answer_with_meta(prompt, temperature=temperature)
    return {
        "query": question,
        "raw_answer": meta["answer"],
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
        "temperature": meta["temperature"],
        "fallback_reason": None,
    }


@traceable(run_type="chain", name="web_app.hybrid_mode")
def run_hybrid(file_path: str, document_text: str, question: str) -> dict:
    try:
        return run_rag(file_path, question)
    except Exception as e:
        print(f"[HYBRID] Full pipeline failed, falling back to direct LLM: {type(e).__name__}: {e}", file=sys.stderr)
        result = run_direct(document_text, question)
        result["fallback_reason"] = f"{type(e).__name__}: {e}"
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


def render_result(mode_key: str, result: dict):
    """Show the answer, then a toggle button that reveals metrics on demand."""
    st.subheader("Answer")
    st.write(result["raw_answer"])

    show_flag = f"show_metrics_{mode_key}"
    if show_flag not in st.session_state:
        st.session_state[show_flag] = False

    label = "📊 Hide metrics" if st.session_state[show_flag] else "📊 Show metrics"
    if st.button(label, key=f"toggle_{show_flag}"):
        st.session_state[show_flag] = not st.session_state[show_flag]

    if st.session_state[show_flag]:
        render_metrics(result)


def log_to_history(mode: str, question: str, result: dict, document_name: str) -> None:
    """Log a query to history after it completes."""
    if not history_enabled or not st.session_state.history_manager:
        return
    
    try:
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
        }
        
        # Log to history
        st.session_state.history_manager.add_question(
            question=question,
            answer=result.get("raw_answer", ""),
            mode=mode,
            metrics_dict=metrics_dict,
            document_name=document_name
        )
    except Exception as e:
        print(f"[HISTORY] Failed to log question: {e}", file=sys.stderr)


def render_history_sidebar() -> None:
    """Display recent questions for current document in sidebar (hidden - background tracking only)."""
    # History is tracked but not displayed in sidebar anymore
    # Users interact via chat interface instead
    pass


def render_chat_history() -> None:
    """Display conversation history as a clean chat interface with responsive margins."""
    if not history_enabled or not st.session_state.history_manager:
        return
    
    current_doc = st.session_state.get("uploaded_name", None)
    if not current_doc:
        return
    
    # Get recent questions for this document
    history_limit = int(os.getenv("HISTORY_LIMIT", "10"))
    recent = st.session_state.history_manager.get_recent_questions(
        document_name=current_doc,
        limit=history_limit
    )
    
    if not recent:
        return
    
    # Display conversation (reverse order so newest is at bottom)
    st.markdown("### 💬 Conversation")
    
    # Responsive chat container with margins
    st.markdown("""
    <style>
        .chat-container {
            max-width: 900px;
            margin: 0 auto;
            padding: 0 12px;
        }
        .chat-bubble-user {
            background-color: #e3f2fd;
            padding: 12px 16px;
            border-radius: 12px;
            margin-bottom: 12px;
            border-left: 4px solid #2196f3;
            margin-right: 40px;
        }
        .chat-bubble-bot {
            background-color: #e8f5e9;
            padding: 12px 16px;
            border-radius: 12px;
            margin-bottom: 12px;
            border-left: 4px solid #4caf50;
            margin-left: 40px;
        }
        .chat-timestamp {
            font-size: 0.8em;
            color: #666;
        }
        .chat-mode-badge {
            display: inline-block;
            background-color: #f0f0f0;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-left: 4px;
        }
    </style>
    <div class="chat-container">
    """, unsafe_allow_html=True)
    
    # Display each conversation turn
    for entry in reversed(recent):
        timestamp = entry.get("timestamp", "")[:16]
        mode = entry.get("mode", "")
        question = entry.get("question", "")
        answer = entry.get("answer", "")
        
        # Question bubble (user - light blue)
        st.markdown(f"""
        <div class="chat-bubble-user">
            <strong>You</strong> <span class="chat-timestamp">{timestamp}</span><br>
            {question}
        </div>
        """, unsafe_allow_html=True)
        
        # Answer bubble (bot - light green)
        st.markdown(f"""
        <div class="chat-bubble-bot">
            <strong>DocuSearch</strong> <span class="chat-mode-badge">{mode}</span><br>
            {answer}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


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


if "file_path" not in st.session_state:
    st.session_state.file_path = None
if "document_text" not in st.session_state:
    st.session_state.document_text = None
if "extraction_seconds" not in st.session_state:
    st.session_state.extraction_seconds = None
if "results" not in st.session_state:
    st.session_state.results = {}
if "last_question" not in st.session_state:
    st.session_state.last_question = ""

uploaded = st.file_uploader("Upload a PDF, DOCX or TXT file", type=["pdf", "docx", "txt"])

if uploaded is not None:
    if st.session_state.get("uploaded_name") != uploaded.name:
        st.session_state.uploaded_name = uploaded.name
        st.session_state.results = {}
        
        # Save file
        try:
            st.session_state.file_path = save_uploaded(uploaded)
            st.info(f"📁 File saved: {uploaded.name} ({uploaded.size} bytes)")
        except Exception as e:
            st.error(f"❌ Failed to save file: {e}")
            st.session_state.document_text = None
            st.session_state.file_path = None
            import traceback
            traceback.print_exc()
        
        # Extract text
        if st.session_state.file_path:
            st.info("⏳ Extracting text from document...")
            t0 = time.perf_counter()
            try:
                st.session_state.document_text = extract_text(st.session_state.file_path)
                st.session_state.extraction_seconds = time.perf_counter() - t0
                size_mb = len(st.session_state.document_text) / (1024 * 1024)
                st.success(
                    f"✅ Extracted {len(st.session_state.document_text)} chars ({size_mb:.2f} MB) "
                    f"in {st.session_state.extraction_seconds:.2f}s"
                )
            except RuntimeError as e:
                # OCR-related errors
                st.warning(f"⚠️ **Note on scanned PDFs**: {e}")
                st.info("📌 **Tip**: For best results, use PDFs with selectable text (not scanned images). "
                       "If you have a scanned PDF in a non-English language, OCR may need configuration.")
                st.session_state.document_text = None
                print(f"[WARNING] Text extraction (OCR): {e}", file=sys.stderr)
            except Exception as e:
                st.error(f"❌ Failed to extract text: {type(e).__name__}: {e}")
                st.session_state.document_text = None
                print(f"[ERROR] Text extraction failed: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
else:
    # No file uploaded yet - show helpful message
    if "uploaded_name" not in st.session_state:
        st.info("👆 Please upload a document to get started")

# Render history sidebar
render_history_sidebar()

# Initialize chat history for conversation
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# If document is uploaded, show chat interface
if st.session_state.document_text:
    st.markdown("---")
    st.markdown("### 💬 Ask Your Document")
    
    # Show conversation history
    render_chat_history()
    
    # Show aggregate metrics for all questions
    render_aggregate_metrics()
    
    # Chat input area
    st.markdown("---")
    
    # Mode selector
    col_mode, col_spacer = st.columns([2, 3])
    with col_mode:
        mode = st.radio(
            "Select Mode:",
            options=["Direct LLM", "RAG", "Hybrid"],
            horizontal=True,
            key="chat_mode_selector"
        )
    
    # Chat input
    question = st.chat_input("Ask a question about the document...", key="chat_input")
    
    if question:
        # Disable RAG/Hybrid on mobile
        if is_mobile and mode in ["RAG", "Hybrid"]:
            st.error("❌ RAG and Hybrid modes are not available on mobile. Using Direct LLM instead.")
            mode = "Direct LLM"
        
        # Show processing message
        with st.spinner(f"⏳ Processing with {mode} mode..."):
            try:
                # Execute the appropriate mode
                if mode == "Direct LLM":
                    result = run_direct(st.session_state.document_text, question)
                elif mode == "RAG":
                    result = run_rag(st.session_state.file_path, question)
                elif mode == "Hybrid":
                    result = run_hybrid(st.session_state.file_path, st.session_state.document_text, question)
                
                # Log to history
                log_to_history(mode, question, result, st.session_state.get("uploaded_name", "unknown"))
                
                # Add to chat display (will show on next render)
                st.success(f"✅ {mode} completed!")
                st.rerun()
                
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
