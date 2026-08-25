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
        if hasattr(st, 'secrets') and st.secrets:
            print(f"[INIT] st.secrets available, loading...", file=sys.stderr)
            # Try direct dict iteration first
            try:
                for key, value in st.secrets.items():
                    converted = _to_env_string(value)
                    os.environ[key] = converted
                    if "LANGSMITH" in key or "LLM" in key:
                        print(f"[INIT] Set {key} = {converted[:30]}...", file=sys.stderr)
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
                            print(f"[INIT] Set {key} = {converted[:30]}...", file=sys.stderr)
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
from src.pipeline import build_pipeline, answer_question
from src.prompt_loader import load_prompt_with_temperature
from src.i18n import translate, get_user_language, add_language_selector_sidebar

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

st.set_page_config(page_title="AI DocuSearch", layout="wide")

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
    st.info(
        "📱 **Mobile Device Detected**: Hybrid mode intelligently adapts to your device's capabilities. "
        "It will use fast, efficient processing optimized for mobile."
    )

st.title("DocuSearch")
st.markdown(
    "Don't remember what a document is all about? Upload your document, ask a question, "
    "and get instant answers using AI."
)


def save_uploaded(uploaded_file):
    suffix = os.path.splitext(uploaded_file.name)[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getbuffer())
    tmp.flush()
    tmp.close()
    return tmp.name


@traceable(run_type="chain", name="web_app.rag_mode")
def run_rag(file_path: str, question: str, document_info: str = "Unknown") -> dict:
    t0 = time.perf_counter()
    pipeline = build_pipeline(file_path, use_embeddings=True)
    build_seconds = time.perf_counter() - t0
    result = answer_question(pipeline, question, document_info=document_info)
    result["build_seconds"] = build_seconds
    result["total_seconds"] += build_seconds
    result["fallback_reason"] = None
    return result


@traceable(run_type="chain", name="web_app.direct_llm_mode")
def run_direct(document_text: str, question: str, document_info: str = "Unknown") -> dict:
    prompt, temperature = load_prompt_with_temperature("direct_llm_prompt", document_text=document_text, question=question, document_info=document_info)
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
def run_hybrid(file_path: str, document_text: str, question: str, document_info: str = "Unknown") -> dict:
    print(f"[HYBRID] Starting Hybrid mode for question: {question[:50]}...", file=sys.stderr)
    try:
        print(f"[HYBRID] Attempting RAG pipeline...", file=sys.stderr)
        result = run_rag(file_path, question, document_info=document_info)
        print(f"[HYBRID] RAG succeeded, answer length: {len(result.get('raw_answer', ''))} chars", file=sys.stderr)
        return result
    except Exception as e:
        print(f"[HYBRID] RAG failed: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(f"[HYBRID] Falling back to Direct LLM mode...", file=sys.stderr)
        result = run_direct(document_text, question, document_info=document_info)
        result["fallback_reason"] = f"{type(e).__name__}: {e}"
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
    """Display recent questions for current document in sidebar (hidden - background tracking only)."""
    # History is tracked but not displayed in sidebar anymore
    # Users interact via chat interface instead
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
            font-size: 14px;
            flex-shrink: 0;
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
        timestamp = entry.get("timestamp", "")[:16]
        mode = entry.get("mode", "")
        question = entry.get("question", "")
        answer = entry.get("answer", "")
        
        # User message (left-aligned)
        st.markdown(f"""
        <div class="chat-message user">
            <div class="chat-avatar user">YOU</div>
            <div>
                <div class="chat-bubble user">{question}</div>
                <div class="chat-info user">{timestamp}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Bot message (right-aligned)
        st.markdown(f"""
        <div class="chat-message bot">
            <div>
                <div class="chat-bubble bot">{answer}</div>
                <div class="chat-info bot">{mode}</div>
            </div>
            <div class="chat-avatar bot">🤖</div>
        </div>
        """, unsafe_allow_html=True)


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
        
        # Save file
        try:
            st.session_state.file_path = save_uploaded(uploaded)
            st.info(f"{translate('file_saved')}: {uploaded.name} ({uploaded.size} bytes)")
        except Exception as e:
            st.error(f"{translate('failed_save')}: {e}")
            st.session_state.document_text = None
            st.session_state.page_count = None
            st.session_state.file_path = None
            import traceback
            traceback.print_exc()
        
        # Extract text
        if st.session_state.file_path:
            st.info(translate("extracting"))
            t0 = time.perf_counter()
            try:
                st.session_state.document_text = extract_text(st.session_state.file_path)
                st.session_state.extraction_seconds = time.perf_counter() - t0
                size_mb = len(st.session_state.document_text) / (1024 * 1024)
                
                # Get page count if it's a PDF
                st.session_state.page_count = None
                if st.session_state.file_path.lower().endswith('.pdf'):
                    st.session_state.page_count = get_pdf_page_count(st.session_state.file_path)
                
                page_info = ""
                if st.session_state.page_count:
                    page_info = f", {st.session_state.page_count} {translate('pages')}"
                
                st.success(
                    f"{translate('extracted')} {len(st.session_state.document_text)} {translate('chars')} "
                    f"({size_mb:.2f} {translate('mb')}){page_info} "
                    f"{translate('in')} {st.session_state.extraction_seconds:.2f}{translate('seconds')}"
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
                st.session_state.page_count = None
                print(f"[WARNING] Text extraction (OCR): {e}", file=sys.stderr)
            except Exception as e:
                st.error(f"{translate('failed_extract')}: {type(e).__name__}: {e}")
                st.session_state.document_text = None
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

# Add language selector to sidebar
add_language_selector_sidebar()

# Initialize chat history for conversation
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# If document is uploaded, show chat interface
if st.session_state.document_text:
    # Chat container
    st.markdown("<div style='background-color: #f9f9f9; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; @media (prefers-color-scheme: dark) { background-color: #1e1e1e; border-color: #333; }'>" , unsafe_allow_html=True)
    
    # Hybrid mode is the only mode
    mode = "Hybrid"
    
    st.markdown("---")
    
    # Show conversation history
    render_chat_history()
    
    st.markdown("---")
    
    # Chat input
    question = st.chat_input(translate("ask_question"), key="chat_input")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    if question:
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
                result = run_hybrid(st.session_state.file_path, st.session_state.document_text, question, document_info=document_info)
                
                print(f"[CHAT] Got result with keys: {list(result.keys())}", file=sys.stderr)
                print(f"[CHAT] Result raw_answer length: {len(result.get('raw_answer', ''))} chars", file=sys.stderr)
                
                # Log to history
                print(f"[CHAT] Calling log_to_history...", file=sys.stderr)
                log_to_history(mode, question, result, st.session_state.get("uploaded_name", "unknown"))
                print(f"[CHAT] log_to_history completed", file=sys.stderr)
                
                # Add to chat display (will show on next render)
                st.success(f"{translate('completed')} {mode} completed!")
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
