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

load_dotenv()

from src.ingest import extract_text
from src.ai_query import generate_answer_with_meta
from src.pipeline import build_pipeline, answer_question
from src.prompt_loader import load_prompt_with_temperature

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

try:
    from langsmith import traceable
except Exception:
    # LangSmith is optional; no-op decorator keeps tracing calls safe when it's not installed.
    from typing import Callable, TypeVar

    _F = TypeVar("_F", bound=Callable[..., object])

    def traceable(*_args, **_kwargs) -> Callable[[_F], _F]:
        def _decorator(fn: _F) -> _F:
            return fn
        return _decorator

st.set_page_config(page_title="DocuSearch", layout="wide")

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
    "then run in it one or all the options below to see the response."
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

question = st.text_input("Ask a question about the document")
if question != st.session_state.last_question:
    st.session_state.last_question = question
    st.session_state.results = {}

can_run = bool(st.session_state.document_text) and bool(question)

# On mobile, show only Direct LLM mode; on desktop, show all three modes
if is_mobile:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("⚡ Direct LLM Mode (Recommended for Mobile)")
    st.markdown(
        "Sends the entire extracted document text directly to the LLM — no chunking, "
        "no embeddings, no retrieval step. **This works best on mobile.**"
    )
    if st.button("Run Direct LLM", disabled=not can_run, key="run_direct"):
        st.info("⏳ Processing... this may take 10-30 seconds")
        try:
            result = run_direct(st.session_state.document_text, question)
            st.session_state.results["Direct LLM"] = result
            st.success("✅ Query completed!")
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            st.error(f"❌ **Error**: {error_msg}")
            st.info("**Troubleshooting:**\n- Check your API key in Streamlit secrets\n- Try with a smaller document\n- Check the Streamlit Cloud logs for details")
            print(f"[ERROR] Direct LLM failed: {error_msg}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    if "Direct LLM" in st.session_state.results:
        render_result("Direct LLM", st.session_state.results["Direct LLM"])
else:
    # Desktop version: show all three tabs
    tab_rag, tab_direct, tab_hybrid = st.tabs(["🔎 RAG Mode", "⚡ Direct LLM Mode", "🔀 Hybrid Mode"])

    with tab_rag:
        st.markdown(
            "Full pipeline: chunk the document, build an embedding index, retrieve the most "
            "relevant chunks, then ask the LLM using only that context."
        )
        if st.button("Run RAG", disabled=not can_run, key="run_rag"):
            st.info("⏳ Processing... this may take 30-60 seconds (building embeddings)")
            try:
                result = run_rag(st.session_state.file_path, question)
                st.session_state.results["RAG"] = result
                st.success("✅ RAG completed!")
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                st.error(f"❌ **Error in RAG mode**: {error_msg}")
                print(f"[ERROR] RAG failed: {error_msg}", file=sys.stderr)
                import traceback
                traceback.print_exc()
        if "RAG" in st.session_state.results:
            render_result("RAG", st.session_state.results["RAG"])

    with tab_direct:
        st.markdown(
            "Sends the entire extracted document text directly to the LLM — no chunking, "
            "no embeddings, no retrieval step."
        )
        if st.button("Run Direct LLM", disabled=not can_run, key="run_direct_desktop"):
            st.info("⏳ Processing... this may take 10-30 seconds")
            try:
                result = run_direct(st.session_state.document_text, question)
                st.session_state.results["Direct LLM"] = result
                st.success("✅ Query completed!")
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                st.error(f"❌ **Error**: {error_msg}")
                st.info("**Troubleshooting:**\n- Check your API key in Streamlit secrets\n- Try with a smaller document\n- Check the Streamlit Cloud logs for details")
                print(f"[ERROR] Direct LLM failed: {error_msg}", file=sys.stderr)
                import traceback
                traceback.print_exc()
        if "Direct LLM" in st.session_state.results:
            render_result("Direct LLM", st.session_state.results["Direct LLM"])

    with tab_hybrid:
        st.markdown(
            "Tries the full RAG pipeline first; automatically falls back to Direct LLM mode "
            "if the embedding pipeline fails (e.g. low memory or a missing dependency)."
        )
        if st.button("Run Hybrid", disabled=not can_run, key="run_hybrid"):
            st.info("⏳ Processing... trying RAG, will fallback to Direct LLM if needed")
            try:
                result = run_hybrid(
                    st.session_state.file_path, st.session_state.document_text, question
                )
                st.session_state.results["Hybrid"] = result
                st.success("✅ Hybrid completed!")
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                st.error(f"❌ **Error in Hybrid mode**: {error_msg}")
                print(f"[ERROR] Hybrid failed: {error_msg}", file=sys.stderr)
                import traceback
                traceback.print_exc()
        if "Hybrid" in st.session_state.results:
            render_result("Hybrid", st.session_state.results["Hybrid"])

if len(st.session_state.results) > (1 if is_mobile else 1):
    if not is_mobile:  # Only show comparison on desktop
        st.markdown("---")
        if "show_comparison" not in st.session_state:
            st.session_state.show_comparison = False
        compare_label = "📊 Hide mode comparison" if st.session_state.show_comparison else "📊 Show mode comparison"
        if st.button(compare_label, key="toggle_comparison"):
            st.session_state.show_comparison = not st.session_state.show_comparison

        if st.session_state.show_comparison:
            st.subheader("Compare modes")
            rows = []
            for mode_name, r in st.session_state.results.items():
                rows.append(
                    {
                        "Mode": mode_name,
                        "Total time (s)": round(r["total_seconds"], 2),
                        "Chunks used": r["chunk_count"],
                        "Context chars": r["context_chars"],
                        "Temperature": r["temperature"],
                        "Prompt tokens": r["prompt_tokens"],
                        "Completion tokens": r["completion_tokens"],
                        "Total tokens": r["total_tokens"],
                        "Tokens estimated?": "Yes" if r["estimated_tokens"] else "No",
                        "Live API": "Yes" if r["used_live_api"] else "No",
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)

# st.markdown("---")
# st.markdown(
    # "**Safe default**: RAG/Hybrid mode automatically falls back to lightweight keyword search "
    # "if embedding models can't be loaded, so the app never crashes the browser."
# )
